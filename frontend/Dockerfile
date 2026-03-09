FROM node:20-alpine

WORKDIR /app

# Copy only package files first for layer caching
COPY package.json vite.config.js index.html ./

# Clean install (no Windows node_modules leaking in due to .dockerignore)
RUN npm install --legacy-peer-deps

# Copy source directory
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev"]
