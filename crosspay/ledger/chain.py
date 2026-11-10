"""
Risk-Adaptive Smart Contract Settlement for SME Cross-Border Payments
Module: Blockchain Ledger & Smart Contract Simulation Engine

Features:
- Cryptographic SHA-256 block hashing and tamper-proof chain verification
- Proof-of-Work (PoW) consensus simulation for block mining
- Smart Contract execution rules mirroring the Solidity contract:
    * KYC Validation Enforcement
    * LOW RISK -> Auto-Approve -> Smart Contract execution -> Block mined on-chain
    * MEDIUM RISK -> Hold in Escrow -> Pending manual verification -> Not mined
    * HIGH RISK -> Blocked -> Smart Contract rejects -> Ledger settlement denied
- Persistent storage to JSON ledger file
"""

import hashlib
import json
import os
import time
from datetime import datetime


class Block:
    def __init__(self, index, timestamp, transactions, previous_hash, nonce=0, hash_val=None):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions  # List of approved transaction dicts
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash_val or self.calculate_hash()

    def calculate_hash(self):
        block_content = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }
        encoded = json.dumps(block_content, sort_keys=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    def mine_block(self, difficulty=2):
        target = "0" * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            transactions=data["transactions"],
            previous_hash=data["previous_hash"],
            nonce=data["nonce"],
            hash_val=data["hash"]
        )


class Blockchain:
    def __init__(self, ledger_path, difficulty=2):
        self.ledger_path = ledger_path
        self.difficulty = difficulty
        self.chain = []
        self.load_chain()

    def create_genesis_block(self):
        genesis_tx = [{
            "transaction_id": "GENESIS-0000",
            "sender": "SME-SYSTEM-ROOT",
            "receiver": "NETWORK-GENESIS",
            "amount": 0.0,
            "currency": "SYS",
            "risk_level": "LOW",
            "status": "APPROVED",
            "smart_contract_status": "CONTRACT_INITIALIZED",
            "timestamp": "2026-01-01 00:00:00",
            "notes": "Genesis Block - Risk-Adaptive SME Cross-Border Settlement Network initialized"
        }]
        genesis_block = Block(0, "2026-01-01 00:00:00", genesis_tx, "0" * 64, nonce=42)
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        self.save_chain()

    def get_latest_block(self):
        if not self.chain:
            self.create_genesis_block()
        return self.chain[-1]

    def add_block_for_transaction(self, approved_tx):
        """
        Only APPROVED transactions can be added to the blockchain ledger!
        Creates and mines a new block containing this settlement.
        """
        latest_block = self.get_latest_block()
        new_block = Block(
            index=len(self.chain),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            transactions=[approved_tx],
            previous_hash=latest_block.hash
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.save_chain()
        return new_block

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Re-calculate hash check
            if current.hash != current.calculate_hash():
                return False, f"Block {current.index} hash mismatch!"

            # Check chain link
            if current.previous_hash != previous.hash:
                return False, f"Block {current.index} previous_hash does not match Block {previous.index} hash!"

            # Check proof of work
            if not current.hash.startswith("0" * self.difficulty):
                return False, f"Block {current.index} does not satisfy difficulty requirement!"

        return True, "Blockchain ledger integrity verified. All cryptographic hashes intact."

    def save_chain(self):
        try:
            data = [block.to_dict() for block in self.chain]
            os.makedirs(os.path.dirname(os.path.abspath(self.ledger_path)), exist_ok=True)
            with open(self.ledger_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving blockchain ledger: {e}")

    def load_chain(self):
        if os.path.exists(self.ledger_path):
            try:
                with open(self.ledger_path, "r") as f:
                    data = json.load(f)
                    self.chain = [Block.from_dict(b) for b in data]
                    if not self.chain:
                        self.create_genesis_block()
            except Exception as e:
                print(f"Error loading blockchain ledger: {e}")
                self.create_genesis_block()
        else:
            self.create_genesis_block()


class SmartContractEngine:
    """
    Executes the Smart Contract Settlement logic.
    Governs whether a transaction is Approved, Held, or Blocked.
    """
    CONTRACT_ADDRESS = "0x9E7bC432851Db070c797bAf315cFE0D39B8F2A18"
    ABI_VERSION = "v1.2.0-RiskAdaptive"

    def __init__(self, blockchain_instance):
        self.blockchain = blockchain_instance

    def evaluate_settlement(self, kyc_status, tx_data, risk_level, risk_score):
        """
        Executes smart contract settlement rules:
        1. KYC requirement: SME must be VERIFIED.
        2. Risk Level Evaluation:
           - LOW -> APPROVE -> Mint block on Blockchain -> Smart contract executed
           - MEDIUM -> HOLD -> Place in compliance hold -> Block NOT mined
           - HIGH -> BLOCK -> Reject transaction -> Block NOT mined
        """
        tx_id = tx_data['transaction_id']

        # Rule 1: KYC Validation check
        if kyc_status != 'VERIFIED':
            return {
                'decision': 'REJECTED',
                'risk_level': risk_level,
                'risk_score': risk_score,
                'smart_contract_status': 'REJECTED_UNVERIFIED_KYC',
                'blockchain_hash': 'NOT RECORDED (KYC UNVERIFIED)',
                'block_number': None,
                'contract_address': self.CONTRACT_ADDRESS,
                'execution_message': 'Smart Contract Guard: SME account KYC is not verified.'
            }

        # Rule 2: Risk-Adaptive Evaluation
        if risk_level == 'LOW':
            decision = 'APPROVED'
            smart_contract_status = 'EXECUTED_SETTLED'
            
            # Generate deterministic cryptographic transaction payload hash including currency conversion snapshot
            src_curr = tx_data.get('source_currency', tx_data.get('currency', 'USD'))
            tgt_curr = tx_data.get('target_currency', src_curr)
            conv_amt = tx_data.get('converted_amount', tx_data['amount'])
            rate = tx_data.get('exchange_rate', 1.0)
            provider = tx_data.get('exchange_rate_provider', 'N/A')
            rate_time = tx_data.get('rate_timestamp', 'N/A')

            payload_str = f"{tx_id}:{tx_data['sender']}:{tx_data['receiver']}:{tx_data['amount']}:{src_curr}:{conv_amt}:{tgt_curr}:{rate}:{risk_score}:{time.time()}"
            tx_hash = "0x" + hashlib.sha256(payload_str.encode()).hexdigest()
            
            # Package transaction for blockchain recording
            record_tx = {
                "transaction_id": tx_id,
                "sender": tx_data['sender'],
                "receiver": tx_data['receiver'],
                "sender_country": tx_data.get('sender_country', 'N/A'),
                "receiver_country": tx_data.get('receiver_country', 'N/A'),
                "amount": tx_data['amount'],
                "currency": src_curr,
                "source_currency": src_curr,
                "target_currency": tgt_curr,
                "exchange_rate": rate,
                "converted_amount": conv_amt,
                "exchange_rate_provider": provider,
                "rate_timestamp": rate_time,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "decision": decision,
                "tx_hash": tx_hash,
                "smart_contract_status": smart_contract_status,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Mine and add block to local blockchain
            block = self.blockchain.add_block_for_transaction(record_tx)
            
            return {
                'decision': decision,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'smart_contract_status': smart_contract_status,
                'blockchain_hash': tx_hash,
                'block_number': block.index,
                'contract_address': self.CONTRACT_ADDRESS,
                'block_hash': block.hash,
                'execution_message': f'Smart Contract Settlement executed successfully on Block #{block.index}. Ledger updated.'
            }

        elif risk_level == 'MEDIUM':
            decision = 'HOLD'
            smart_contract_status = 'HELD_IN_ESCROW'
            
            return {
                'decision': decision,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'smart_contract_status': smart_contract_status,
                'blockchain_hash': 'PENDING_ADDITIONAL_VERIFICATION',
                'block_number': None,
                'contract_address': self.CONTRACT_ADDRESS,
                'execution_message': 'Smart Contract Trigger: Moderate risk pattern detected. Transaction held in escrow pending secondary compliance audit.'
            }

        else:  # HIGH RISK
            decision = 'BLOCKED'
            smart_contract_status = 'REJECTED_BLOCKED'

            return {
                'decision': decision,
                'risk_level': risk_level,
                'risk_score': risk_score,
                'smart_contract_status': smart_contract_status,
                'blockchain_hash': 'NOT RECORDED (SECURITY BLOCK)',
                'block_number': None,
                'contract_address': self.CONTRACT_ADDRESS,
                'execution_message': 'Smart Contract Policy Rule: High risk anomaly detected. Transaction blocked to prevent fraudulent SME drainage.'
            }

    def release_hold(self, tx_data):
        """
        Compliance administrator releases a previously held transaction.
        Mines block and completes smart contract settlement.
        """
        tx_id = tx_data['transaction_id']
        src_curr = tx_data.get('source_currency', tx_data.get('currency', 'USD'))
        tgt_curr = tx_data.get('target_currency', src_curr)
        conv_amt = tx_data.get('converted_amount', tx_data['amount'])
        rate = tx_data.get('exchange_rate', 1.0)
        provider = tx_data.get('exchange_rate_provider', 'N/A')
        rate_time = tx_data.get('rate_timestamp', 'N/A')

        payload_str = f"RELEASED:{tx_id}:{tx_data['sender']}:{tx_data['amount']}:{src_curr}:{conv_amt}:{tgt_curr}:{time.time()}"
        tx_hash = "0x" + hashlib.sha256(payload_str.encode()).hexdigest()

        record_tx = {
            "transaction_id": tx_id,
            "sender": tx_data['sender'],
            "receiver": tx_data['receiver'],
            "sender_country": tx_data.get('sender_country', 'N/A'),
            "receiver_country": tx_data.get('receiver_country', 'N/A'),
            "amount": tx_data['amount'],
            "currency": src_curr,
            "source_currency": src_curr,
            "target_currency": tgt_curr,
            "exchange_rate": rate,
            "converted_amount": conv_amt,
            "exchange_rate_provider": provider,
            "rate_timestamp": rate_time,
            "risk_level": tx_data.get('risk_level', 'MEDIUM'),
            "risk_score": tx_data.get('risk_score', 50.0),
            "decision": "APPROVED",
            "tx_hash": tx_hash,
            "smart_contract_status": "EXECUTED_SETTLED_POST_AUDIT",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        block = self.blockchain.add_block_for_transaction(record_tx)
        return {
            'tx_hash': tx_hash,
            'block_number': block.index,
            'block_hash': block.hash
        }

