# Stage 1: Build the React application
FROM node:20-alpine as builder

WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock) first
# This helps Docker cache these layers, speeding up rebuilds if dependencies don't change
COPY package.json ./
COPY package-lock.json ./ 

# Install frontend dependencies
RUN npm install # Or yarn install

# Copy the rest of the frontend source code
COPY . .

# Build the React application for production
# This runs the build script defined in your package.json (which should be 'vite build')
RUN npm run build

# Stage 2: Serve the built React application with Nginx
# Start a new stage from a lightweight Nginx image
FROM nginx:alpine

# Copy the built application files from the 'builder' stage
# Vite's default output directory is 'dist'
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy your custom Nginx configuration file
# This is essential for handling client-side routing in SPAs
# Make sure you have an nginx.conf file in your frontend directory
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 as Nginx listens on this port by default
EXPOSE 80

# Command to run Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]
