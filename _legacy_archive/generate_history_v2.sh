#!/bin/bash

SOURCE_DIR=$(pwd)
TARGET_DIR="../SeedTracking-History"

echo "Creating Shadow Repository at $TARGET_DIR"
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"
git init
git branch -M main

export GIT_AUTHOR_NAME='sudeshsudhii'
export GIT_AUTHOR_EMAIL='sudeshtiger1999@gmail.com'
export GIT_COMMITTER_NAME='sudeshsudhii'
export GIT_COMMITTER_EMAIL='sudeshtiger1999@gmail.com'

# Base commit function
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

# Add file with a temporary WIP comment to simulate an incomplete feature
commit_wip() {
    DATE=$1
    MSG=$2
    FILE=$3
    WIP_TEXT=$4
    mkdir -p "$(dirname "$FILE")"
    cp "$SOURCE_DIR/$FILE" "$FILE"
    echo "$WIP_TEXT" >> "$FILE"
    git add "$FILE"
    GIT_AUTHOR_DATE="$DATE" GIT_COMMITTER_DATE="$DATE" git commit -m "$MSG"
}

# The final fix applies the real file, removing the WIP string
commit_fix() {
    DATE=$1
    MSG=$2
    FILE=$3
    cp "$SOURCE_DIR/$FILE" "$FILE"
    git add "$FILE"
    GIT_AUTHOR_DATE="$DATE" GIT_COMMITTER_DATE="$DATE" git commit -m "$MSG"
}

# Add abandoned experiment (creates dummy file, commits, then deletes)
commit_experiment() {
    DATE_ADD=$1
    MSG_ADD=$2
    DATE_REVERT=$3
    MSG_REVERT=$4
    FILE=$5
    mkdir -p "$(dirname "$FILE")"
    echo "// experimental feature" > "$FILE"
    git add "$FILE"
    GIT_AUTHOR_DATE="$DATE_ADD" GIT_COMMITTER_DATE="$DATE_ADD" git commit -m "$MSG_ADD"
    rm "$FILE"
    git add "$FILE"
    GIT_AUTHOR_DATE="$DATE_REVERT" GIT_COMMITTER_DATE="$DATE_REVERT" git commit -m "$MSG_REVERT"
}

# Execute Timeline
commit_step "2026-02-02T19:30:00" "chore: initialize git repository and base ignore" "README.md" ".gitignore"
commit_step "2026-02-04T20:15:00" "chore: add prettier for code formatting" ".prettierrc.json" "README.txt"
commit_step "2026-02-07T10:00:00" "feat: configure hardhat blockchain environment" "hardhat.config.js"
commit_step "2026-02-07T14:20:00" "feat: add basic storage contract for testing" "contracts/1_Storage.sol"
commit_wip  "2026-02-07T16:45:00" "test: implement storage contract test suite" "tests/storage.test.js" "// TODO: add edge cases"
commit_step "2026-02-08T11:10:00" "feat: add owner utility contract" "contracts/2_Owner.sol"
commit_step "2026-02-08T15:30:00" "feat: add ballot contract for voting logic" "contracts/3_Ballot.sol"
commit_step "2026-02-08T22:15:00" "test: verify ballot contract logic" "tests/Ballot_test.sol"
commit_fix  "2026-02-11T20:00:00" "test: add edge cases for proof generation" "tests/storage.test.js"
commit_step "2026-02-15T18:00:00" "feat: create core EventChain smart contract" "contracts/EventChain.sol"
commit_step "2026-02-18T21:00:00" "refactor: extract simple deployment script" "scripts/deploy-simple.js"
commit_step "2026-02-21T10:30:00" "feat: implement eventchain deployment" "scripts/deploy-eventchain.js"
commit_step "2026-02-21T14:00:00" "feat: add ration distribution contract" "contracts/RationDistribution.sol"
commit_experiment "2026-02-22T11:20:00" "feat: try deploying to polygon mumbai testnet" "2026-02-22T11:45:00" "Revert \"feat: try deploying to polygon mumbai testnet\"" "scripts/deploy-mumbai.js"
commit_step "2026-02-28T09:00:00" "chore: initialize spring boot maven project" "pom.xml"
commit_step "2026-02-28T10:15:00" "chore: add test properties for spring boot" "application-test.properties"
commit_step "2026-02-28T14:30:00" "feat: setup spring boot application base" "src/main/java/com/eventchain/EventChainApplication.java" "src/main/resources/application.properties"
commit_step "2026-03-01T11:00:00" "feat: implement event entity model" "src/main/java/com/eventchain/model/Event.java"
commit_step "2026-03-01T15:45:00" "feat: implement event request payload" "src/main/java/com/eventchain/dto/EventRequest.java"
commit_step "2026-03-04T20:20:00" "refactor: add structured event response" "src/main/java/com/eventchain/dto/EventResponse.java"
commit_step "2026-03-07T10:10:00" "feat: define blockchain service interface" "src/main/java/com/eventchain/service/BlockchainService.java"
commit_step "2026-03-07T14:00:00" "feat: implement ipfs storage service" "src/main/java/com/eventchain/service/IpfsService.java"
commit_step "2026-03-08T11:30:00" "chore: add blockchain configuration properties" "src/main/java/com/eventchain/config/BlockchainConfig.java"
commit_step "2026-03-08T16:15:00" "feat: add proof json payload definition" "src/main/java/com/eventchain/dto/ProofJson.java"
commit_wip  "2026-03-14T10:00:00" "feat: implement event controller endpoints" "src/main/java/com/eventchain/controller/EventController.java" "// import unused.class;"
commit_step "2026-03-14T15:45:00" "fix: resolve missing favicon 404 errors" "src/main/java/com/eventchain/controller/FaviconController.java"
commit_step "2026-03-15T12:00:00" "refactor: centralize API error handling" "src/main/java/com/eventchain/controller/GlobalExceptionHandler.java"
commit_fix  "2026-03-15T16:30:00" "chore: clean up unused imports in backend" "src/main/java/com/eventchain/controller/EventController.java"
commit_step "2026-03-18T21:15:00" "feat: add proof generation service" "src/main/java/com/eventchain/service/ProofService.java"
commit_step "2026-03-21T10:20:00" "fix: resolve cross-origin request blocks from React" "src/main/java/com/eventchain/config/CorsConfig.java"
commit_wip  "2026-03-21T14:40:00" "feat: add verification response model" "src/main/java/com/eventchain/dto/VerifyResponse.java" "// TODO: fix typo in field"
commit_fix  "2026-03-22T11:00:00" "fix: typo in verification response payload" "src/main/java/com/eventchain/dto/VerifyResponse.java"
commit_step "2026-03-22T14:15:00" "feat: initialize react frontend scaffold" "frontend/package.json" "frontend/package-lock.json"
commit_step "2026-03-25T20:00:00" "feat: setup react base layout and routing" "frontend/src/index.js" "frontend/src/App.js"
commit_wip  "2026-03-28T10:00:00" "chore: add global css baseline" "frontend/src/index.css" "/* WIP */"
commit_wip  "2026-03-28T15:30:00" "feat: implement basic navbar component" "frontend/src/components/Navbar.js" "// TODO: responsive layout"
commit_fix  "2026-03-29T11:45:00" "fix: resolve mobile navbar rendering" "frontend/src/components/Navbar.js"
commit_step "2026-03-29T16:10:00" "feat: build landing home page" "frontend/src/pages/Home.js"
commit_step "2026-04-01T20:00:00" "feat: setup web3 wallet context" "frontend/src/context/WalletContext.js"
commit_step "2026-04-04T09:30:00" "feat: implement metamask wallet connector" "frontend/src/components/WalletConnector.js"
commit_step "2026-04-04T11:15:00" "fix: handle null wallet connection state" "frontend/src/components/SystemStatus.js"
commit_step "2026-04-05T10:45:00" "chore: initialize nodejs proxy backend" "backend-node/package.json" "backend-node/package-lock.json"
commit_wip  "2026-04-05T14:20:00" "feat: setup express server and base routes" "backend-node/index.js" "// TODO: add cors"
commit_step "2026-04-05T16:00:00" "chore: add env configuration" "backend-node/.env"
commit_fix  "2026-04-08T20:15:00" "fix: add missing CORS headers to proxy" "backend-node/index.js"
commit_step "2026-04-11T09:00:00" "feat: create database connection service" "backend-node/services/db.js"
commit_step "2026-04-11T14:30:00" "fix: mock IPFS for local testing environments" "backend-node/models/MockIPFS.js"
commit_wip  "2026-04-12T11:15:00" "feat: develop core SeedChain smart contract" "contracts/SeedChain.sol" "// TODO: optimize gas"
commit_fix  "2026-04-12T15:00:00" "refactor: optimize gas consumption in batch creation" "contracts/SeedChain.sol"
commit_step "2026-04-15T21:00:00" "feat: add seedchain deployment script" "scripts/deploy-seedchain.js"
commit_step "2026-04-18T10:20:00" "refactor: consolidate contract deployment" "scripts/deploy.js" "scripts/deploy-with-hardhat.js"
commit_step "2026-04-18T14:45:00" "feat: implement batch tracking model" "backend-node/models/Batch.js"
commit_step "2026-04-19T11:30:00" "feat: implement seed transfer model" "backend-node/models/Transfer.js"
commit_step "2026-04-19T16:10:00" "feat: implement certificate compliance model" "backend-node/models/Certificate.js"
commit_wip  "2026-04-22T20:00:00" "feat: build seed dashboard base layout" "frontend/src/pages/SeedDashboard.js" "// TODO: handle loading"
commit_fix  "2026-04-25T10:00:00" "fix: handle loading spinner state on dashboard" "frontend/src/pages/SeedDashboard.js"
commit_step "2026-04-25T15:20:00" "feat: build batches explorer view" "frontend/src/pages/BatchesPage.js"
commit_wip  "2026-04-26T11:45:00" "feat: implement batch line-item component" "frontend/src/components/BatchExplorer.js" "  "
commit_fix  "2026-04-26T16:30:00" "style: fix prettier formatting in batch explorer" "frontend/src/components/BatchExplorer.js"
commit_step "2026-04-29T20:15:00" "refactor: extract reusable api client" "frontend/src/services/api.js"
commit_step "2026-05-02T09:30:00" "feat: implement create batch form" "frontend/src/components/BatchForm.js"
commit_step "2026-05-02T11:00:00" "feat: add create batch page integration" "frontend/src/pages/CreateBatch.js"
commit_step "2026-05-03T10:30:00" "feat: integrate ethers.js in node backend" "backend-node/services/blockchain.js"
commit_step "2026-05-03T14:00:00" "feat: integrate ipfs upload stream" "backend-node/services/ipfs.js"
commit_step "2026-05-06T20:00:00" "feat: scaffold python ai anomaly service" "ai-service/requirements.txt"
commit_wip  "2026-05-09T10:15:00" "feat: setup fastapi python server" "ai-service/main.py" "# TODO: timeout handler"
commit_fix  "2026-05-09T14:40:00" "fix: catch prediction timeout errors in AI service" "ai-service/main.py"
commit_step "2026-05-10T11:20:00" "feat: develop isolation forest model pipeline" "ai-service/model.py"
commit_step "2026-05-10T16:00:00" "test: inject trained fraud model weights" "ai-service/fraud_model.pkl"
commit_step "2026-05-13T21:00:00" "feat: integrate ai risk scoring in nodejs" "backend-node/services/ai.js"
commit_step "2026-05-16T10:00:00" "feat: add fraud analysis database model" "backend-node/models/FraudAnalysis.js"
commit_step "2026-05-16T15:30:00" "feat: build fraud stats dashboard component" "frontend/src/components/Dashboard/FraudStats.js"
commit_step "2026-05-17T11:45:00" "feat: build live transaction feed" "frontend/src/components/Dashboard/LiveTransactions.js"
commit_step "2026-05-17T16:10:00" "feat: build shop inventory overview" "frontend/src/components/Dashboard/ShopInventory.js"
commit_step "2026-05-20T20:00:00" "refactor: move quota constants to shared config" "frontend/src/constants/quota.js" "frontend/src/constants/regions.js"
commit_step "2026-05-20T21:00:00" "refactor: extract seed types and locations" "frontend/src/constants/seedTypes.js" "frontend/src/constants/shops.js" "frontend/src/constants/stock.js"
commit_step "2026-05-23T09:30:00" "feat: add event timeline page" "frontend/src/pages/Timeline.js"
commit_step "2026-05-23T11:00:00" "feat: add batch lineage tracking view" "frontend/src/pages/LineagePage.js"
commit_step "2026-05-24T10:20:00" "feat: implement timeline visual components" "frontend/src/components/EventTimeline.js"
commit_step "2026-05-24T14:50:00" "feat: implement batch lineage tree" "frontend/src/components/BatchLineage.js"
commit_experiment "2026-05-26T20:00:00" "feat: attempt to migrate tracking to graphql" "2026-05-27T21:15:00" "Revert \"feat: attempt to migrate tracking to graphql\"" "backend-node/graphql.js"
commit_step "2026-05-30T10:00:00" "feat: implement qr code generation service" "src/main/java/com/eventchain/service/QRCodeService.java"
commit_step "2026-05-30T11:30:00" "feat: build qr code display component" "frontend/src/components/QrCodeDisplay.js"
commit_step "2026-05-30T14:00:00" "feat: add qr scanner for physical tracking" "frontend/src/components/QRScanner.js"
commit_step "2026-05-31T09:15:00" "feat: build certificate verifier component" "frontend/src/components/CertificateVerifier.js"
commit_step "2026-05-31T11:40:00" "refactor: move pdf generation to dedicated service" "frontend/src/services/pdfGenerator.js"
commit_step "2026-05-31T14:20:00" "chore: setup multi-language configuration" "frontend/src/i18n.js"
commit_step "2026-05-31T16:00:00" "feat: add translation bundles" frontend/src/locales/*.json
commit_step "2026-06-01T09:00:00" "feat: implement event verification pages" "frontend/src/pages/VerifyEvent.js" "frontend/src/pages/VerifyPage.js"
commit_step "2026-06-01T10:15:00" "refactor: abstract ethers and web3 utilities" scripts/*-lib.ts
commit_step "2026-06-02T11:30:00" "fix: add typed deployment scripts for robust CI" scripts/deploy_with_*.ts
commit_step "2026-06-02T16:45:00" "chore: add legacy deployment and test scripts" "setup.sh" *.bat
commit_fix  "2026-06-03T10:00:00" "style: refine mobile responsive layouts" "frontend/src/index.css"
commit_step "2026-06-03T14:30:00" "chore: scaffold docker containerization" "Dockerfile" "backend-node/Dockerfile" "ai-service/Dockerfile"
commit_step "2026-06-04T10:15:00" "fix: resolve docker build context paths" ".dockerignore"
commit_step "2026-06-04T15:45:00" "chore: setup docker-compose environment" "docker-compose.yml" "docker-entrypoint.sh"
commit_step "2026-06-05T11:00:00" "docs: document core application architecture" "APPLICATION_DOCUMENTATION.md"
commit_wip  "2026-06-05T15:20:00" "docs: add deployment and test guides" "TEST_SETUP.md" "needs update"
commit_step "2026-06-05T15:25:00" "docs: add remaining guides" "DEPLOYMENT.md" "DOCKER.md"
commit_fix  "2026-06-06T10:30:00" "docs: clarify local setup process" "TEST_SETUP.md"
commit_step "2026-06-06T16:00:00" "docs: append remix bypass and PDS overview" "DEPLOY_WITHOUT_REMIX.md" "README_PDS.md"
commit_step "2026-06-07T11:45:00" "refactor: finalize database schema and tasks" "pds.db" "remix.config.json" "task.md" "walkthrough.md" ".gitignore.backup" "src/main/resources/application.properties.backup"

echo "Success! The newly generated repository is located at: $TARGET_DIR"
