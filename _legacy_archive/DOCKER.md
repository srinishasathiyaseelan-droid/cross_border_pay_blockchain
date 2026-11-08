# Docker Setup for EventChain

This guide explains how to run EventChain using Docker.

## 🐳 Quick Start

### Option 1: Using Docker Compose (Recommended)

1. **Build and run:**
   ```bash
   docker-compose up --build
   ```

2. **Run in detached mode:**
   ```bash
   docker-compose up -d --build
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Stop:**
   ```bash
   docker-compose down
   ```

### Option 2: Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t eventchain:latest .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -p 8080:8080 \
     -p 3000:3000 \
     --name eventchain \
     eventchain:latest
   ```

3. **View logs:**
   ```bash
   docker logs -f eventchain
   ```

4. **Stop:**
   ```bash
   docker stop eventchain
   docker rm eventchain
   ```

## 🔧 Configuration

### Environment Variables

You can configure the application using environment variables:

```bash
docker run -d \
  -p 8080:8080 \
  -p 3000:3000 \
  -e BLOCKCHAIN_CONTRACT_ADDRESS=0xYourContractAddress \
  -e BLOCKCHAIN_PRIVATE_KEY=YourPrivateKey \
  -e IPFS_HOST=127.0.0.1 \
  -e IPFS_PORT=5001 \
  eventchain:latest
```

Or create a `.env` file for docker-compose:

```env
BLOCKCHAIN_NETWORK_URL=https://polygon-rpc.com
BLOCKCHAIN_CONTRACT_ADDRESS=
BLOCKCHAIN_PRIVATE_KEY=
IPFS_HOST=127.0.0.1
IPFS_PORT=5001
IPFS_PROTOCOL=http
```

Then run:
```bash
docker-compose --env-file .env up
```

## 📋 Prerequisites

- Docker 20.10+
- Docker Compose 2.0+ (optional, for docker-compose)

## 🌐 Accessing the Application

After starting the container:

- **Backend API**: http://localhost:8080
- **Frontend**: http://localhost:3000

## 🔍 Troubleshooting

### Check if containers are running:
```bash
docker ps
```

### View container logs:
```bash
docker logs eventchain-app
# or
docker-compose logs -f
```

### Access container shell:
```bash
docker exec -it eventchain-app sh
```

### Rebuild after code changes:
```bash
docker-compose up --build
```

### Clean up:
```bash
# Stop and remove containers
docker-compose down

# Remove images
docker rmi eventchain:latest

# Remove volumes (if any)
docker volume prune
```

## 📝 Notes

1. **IPFS**: If you need IPFS, you can either:
   - Run IPFS separately on your host machine
   - Uncomment the IPFS service in `docker-compose.yml`
   - Connect to an external IPFS node

2. **Blockchain**: The application will start without blockchain/IPFS configured, but those features won't work until configured.

3. **Port Conflicts**: If ports 8080 or 3000 are already in use, modify the port mappings in `docker-compose.yml` or the `docker run` command.

4. **Development**: For development, it's recommended to run backend and frontend separately for hot-reload capabilities.

## 🚀 Production Deployment

For production, consider:

1. **Separate containers**: Run backend and frontend in separate containers for better scalability
2. **Reverse proxy**: Use nginx or traefik as a reverse proxy
3. **Environment variables**: Use secrets management (Docker secrets, Kubernetes secrets, etc.)
4. **Health checks**: The docker-compose.yml includes a health check for the backend
5. **Resource limits**: Add resource limits to docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '1'
         memory: 2G
   ```
