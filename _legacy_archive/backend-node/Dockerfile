FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Copy artifacts from parent if needed, or assume they are mounted/copied in build context
# For simple docker-compose, we can mount volumes or copy in a multi-stage. 
# Here we assume the artifacts folder is copied into the context or we are running in dev mode.

EXPOSE 4000

CMD ["npm", "start"]
