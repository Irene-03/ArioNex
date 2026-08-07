# ================================================================
#   Two-stage Dockerfile for the ArioNex React client (ArioNex Frontend Dockerfile)
#   Optimized build and distribution behind the powerful, ultra-lightweight Nginx web server
# ================================================================

# --- Stage 1: Build and compile the JavaScript and stylesheet files ---
FROM node:20-slim AS builder

WORKDIR /app

# Copy the package configuration files and install dependencies
# (The lockfile is copied along with package.json to benefit from the build cache)
COPY package.json package-lock.json /app/

# Use a mirror registry for faster package installation
RUN npm install --no-audit --no-fund

# Copy the frontend sources and run the final build with Vite
COPY . /app/
RUN npm run build

# --- Stage 2: Serve and distribute the compiled static files ---
FROM nginx:alpine

# Copy the stage 1 build output into the Nginx web server directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the Nginx configuration to support React SPA routes
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Default web server port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
