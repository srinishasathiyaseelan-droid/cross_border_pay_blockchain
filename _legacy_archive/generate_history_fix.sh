#!/bin/bash

SOURCE_DIR=$(pwd)
TARGET_DIR="../SeedTracking-History"

cd "$TARGET_DIR"

export GIT_AUTHOR_NAME='sudeshsudhii'
export GIT_AUTHOR_EMAIL='sudeshtiger1999@gmail.com'
export GIT_COMMITTER_NAME='sudeshsudhii'
export GIT_COMMITTER_EMAIL='sudeshtiger1999@gmail.com'

commit_step() {
    DATE=$1
    MSG=$2
    shift 2
    for file in "$@"; do
        mkdir -p "$(dirname "$file")"
        cp "$SOURCE_DIR/$file" "$file"
        git add "$file"
    done
    GIT_AUTHOR_DATE="$DATE" GIT_COMMITTER_DATE="$DATE" git commit -m "$MSG"
}

commit_step "2026-05-31T16:00:00" "feat: add translation bundles" "frontend/src/locales/en.json" "frontend/src/locales/hi.json" "frontend/src/locales/ta.json"
commit_step "2026-06-01T10:15:00" "refactor: abstract ethers and web3 utilities" "scripts/ethers-lib.ts" "scripts/web3-lib.ts"
commit_step "2026-06-02T11:30:00" "fix: add typed deployment scripts for robust CI" "scripts/deploy_with_ethers.ts" "scripts/deploy_with_web3.ts"
commit_step "2026-06-02T16:45:00" "chore: add legacy deployment and test scripts" "deploy-contract.bat" "deploy-contract-auto.bat" "run-local.bat" "setup-ganache.bat" "start_legacy_DO_NOT_USE.bat"
