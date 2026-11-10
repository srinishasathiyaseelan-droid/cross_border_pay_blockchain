"""Simulated settlement ledger (H2, H7, M3, M4).

- PoW blocks are built in memory inside the payment's DB transaction and stored in the HMAC-signed audit chain
  (crosspay/ledger/audit.py). The audit chain is the source of truth.
- The JSON file at LEDGER_PATH is only a derived explorer view, rebuilt from the audit chain after each commit,
  written atomically (temp file + os.replace) under a file lock, and not tracked in git.
- Every hash is deterministic (no time.time()), so blocks and transaction hashes can be re-verified.
- verify() checks the genesis block, PoW links and difficulty, the audit chain HMACs, and that each transaction row
  still matches its signed audit record.
"""
import hashlib
import json
import logging
import os
import threading
import time

from .audit import AuditChain, canonical
from .filelock import FileLock

log = logging.getLogger(__name__)

GENESIS_TIMESTAMP = "2026-01-01T00:00:00Z"
GENESIS_TX = [{
    "transaction_id": "GENESIS-0000",
    "sender": "SME-SYSTEM-ROOT",
    "receiver": "NETWORK-GENESIS",
    "amount": 0.0,
    "currency": "SYS",
    "decision": "APPROVED",
    "notes": "Genesis block - CrossPay simulated settlement ledger",
}]
# Fields of a transaction row that are signed into its audit record and re-checked by verify().
SIGNED_FIELDS = ("transaction_id", "user_id", "sender", "receiver", "sender_country", "receiver_country",
                 "source_currency", "target_currency", "amount", "exchange_rate", "converted_amount",
                 "normalized_usd_amount", "risk_level", "risk_score", "decision")
NOT_RECORDED = {
    "HOLD": "PENDING_ADDITIONAL_VERIFICATION",
    "BLOCKED": "NOT RECORDED (SECURITY BLOCK)",
    "REJECTED": "NOT RECORDED (REJECTED)",
}


class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0, hash_val=None):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash_val or self.calculate_hash()

    def calculate_hash(self) -> str:
        content = {"index": self.index, "timestamp": self.timestamp, "transactions": self.transactions,
                   "previous_hash": self.previous_hash, "nonce": self.nonce}
        return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

    def mine(self, difficulty: int) -> "Block":
        target = "0" * difficulty
        self.nonce = 0
        self.hash = self.calculate_hash()
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()
        return self

    def to_dict(self) -> dict:
        return {"index": self.index, "timestamp": self.timestamp, "transactions": self.transactions,
                "previous_hash": self.previous_hash, "nonce": self.nonce, "hash": self.hash}

    @classmethod
    def from_dict(cls, d) -> "Block":
        return cls(d["index"], d["timestamp"], d["transactions"], d["previous_hash"], d["nonce"], d["hash"])


def genesis_block(difficulty: int) -> Block:
    return Block(0, GENESIS_TIMESTAMP, GENESIS_TX, "0" * 64).mine(difficulty)


def settlement_record(row: dict, decision: str, decided_at: str) -> dict:
    """The deterministic payload that is hashed, signed and (if approved) mined."""
    rec = {k: row.get(k) for k in SIGNED_FIELDS}
    rec["decision"] = decision
    rec["decided_at"] = decided_at
    return rec


def tx_hash(record: dict) -> str:
    return "0x" + hashlib.sha256(canonical(record).encode()).hexdigest()


class Ledger:
    def __init__(self, view_path: str, difficulty: int, audit: AuditChain):
        self.view_path = view_path
        self.difficulty = difficulty
        self.audit = audit
        self._genesis = genesis_block(difficulty)
        self._lock = threading.Lock()

    # ---- reading -------------------------------------------------------------------------------------------
    def blocks(self, conn) -> list:
        out = [self._genesis]
        for r in conn.execute("SELECT payload FROM audit_chain WHERE record_type IN ('decision', 'release', 'seed') "
                              "ORDER BY id ASC"):
            block = json.loads(r[0]).get("block")
            if block:
                out.append(Block.from_dict(block))
        return out

    def build_block(self, conn, record: dict, timestamp: str) -> Block:
        """Must be called inside the DB transaction that will also append the audit record."""
        last = self.blocks(conn)[-1]
        return Block(last.index + 1, timestamp, [record], last.hash).mine(self.difficulty)

    # ---- verification --------------------------------------------------------------------------------------
    def verify(self, conn) -> dict:
        blocks = self.blocks(conn)
        result = {"valid": True, "message": "", "total_blocks": len(blocks), "audit_records": 0, "mismatches": []}
        expected_genesis = genesis_block(self.difficulty)
        if blocks[0].hash != expected_genesis.hash:
            return {**result, "valid": False, "message": "Genesis block does not match the expected genesis."}
        for prev, cur in zip(blocks, blocks[1:]):
            if cur.hash != cur.calculate_hash():
                return {**result, "valid": False, "message": f"Block {cur.index} hash does not match its contents."}
            if cur.previous_hash != prev.hash:
                return {**result, "valid": False, "message": f"Block {cur.index} is not linked to block {prev.index}."}
            if not cur.hash.startswith("0" * self.difficulty):
                return {**result, "valid": False, "message": f"Block {cur.index} fails the PoW difficulty."}
            if cur.index != prev.index + 1:
                return {**result, "valid": False, "message": f"Block {cur.index} has a gap in numbering."}
        ok, msg, n = self.audit.verify(conn)
        result["audit_records"] = n
        if not ok:
            return {**result, "valid": False, "message": msg}
        mismatches = self.consistency(conn)
        if mismatches:
            return {**result, "valid": False, "mismatches": mismatches,
                    "message": f"{len(mismatches)} transaction row(s) differ from their signed audit record: "
                               + ", ".join(mismatches[:5])}
        result["message"] = (f"Genesis, {len(blocks) - 1} settlement block(s) and {n} HMAC-signed audit record(s) "
                             "verified; every transaction row matches its audit record.")
        return result

    def consistency(self, conn) -> list:
        latest = {}
        for r in conn.execute("SELECT tx_id, payload FROM audit_chain ORDER BY id ASC"):
            latest[r[0]] = json.loads(r[1])
        bad = []
        for tx_id, payload in latest.items():
            row = conn.execute("SELECT * FROM transactions WHERE transaction_id = ?", (tx_id,)).fetchone()
            rec = payload.get("record")
            if row is None or rec is None:
                bad.append(tx_id)
                continue
            row = dict(row)
            for k in SIGNED_FIELDS:
                if k == "decision":
                    continue
                a, b = row.get(k), rec.get(k)
                if isinstance(a, float) or isinstance(b, float):
                    if a is None or b is None or abs(float(a) - float(b)) > 1e-9:
                        bad.append(tx_id)
                        break
                elif a != b:
                    bad.append(tx_id)
                    break
            else:
                if row["decision"] != payload.get("decision") or row.get("blockchain_hash") != payload.get("tx_hash_or_label"):
                    bad.append(tx_id)
        return bad

    # ---- derived JSON view ---------------------------------------------------------------------------------
    def export_view(self, conn) -> None:
        data = [b.to_dict() for b in self.blocks(conn)]
        path = os.path.abspath(self.view_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        with self._lock, FileLock(path + ".lock"):
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            for attempt in range(20):
                try:
                    os.replace(tmp, path)
                    return
                except PermissionError:  # Windows: a reader has the file open; retry briefly
                    time.sleep(0.05 * (attempt + 1))
            log.error("Could not replace ledger view %s; it will be rebuilt on the next commit", path)


class SmartContractEngine:
    """Python simulation of blockchain/smart_contract.sol. The decision itself comes from policy.engine."""

    CONTRACT_ADDRESS = "0x9E7bC432851Db070c797bAf315cFE0D39B8F2A18"
    CONTRACT_LABEL = "simulated (reference design, not deployed)"
    ABI_VERSION = "v1.3.0-RiskAdaptive-sim"

    def __init__(self, config):
        self.review_at = float(config["REVIEW_AT"])
        self.block_at = float(config["BLOCK_AT"])

    def decide(self, kyc_status, risk_level, risk_score, overrides=(), ai_escalations=()):
        from ..policy import engine

        return engine.evaluate(kyc_status, risk_level, risk_score, self.review_at, self.block_at,
                               overrides=overrides, ai_escalations=ai_escalations)

    def preview_decision(self, scored) -> str:
        return self.decide("VERIFIED", scored["level"], scored["score"]).decision
