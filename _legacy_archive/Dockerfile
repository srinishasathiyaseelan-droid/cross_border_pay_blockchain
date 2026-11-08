# Multi-stage Dockerfile for EventChain (Backend + Frontend)

# Stage 1: Build Backend
FROM maven:3.9-eclipse-temurin-17 AS backend-builder
WORKDIR /app
COPY pom.xml .
COPY src ./src
RUN mvn clean package -DskipTests

# Stage 2: Build Frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# Stage 3: Runtime - Combine everything
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# Install Node.js, serve, and wget for health checks
RUN apk add --no-cache nodejs npm wget && \
    npm install -g serve

# Copy backend JAR
COPY --from=backend-builder /app/target/*.jar app.jar

# Copy frontend build
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Copy startup script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8080 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/events || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
