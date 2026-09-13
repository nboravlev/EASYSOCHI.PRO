# Build stage
FROM ubuntu:22.04 as builder

WORKDIR /tmp

# Download and extract Hugo
RUN apt-get update && apt-get install -y wget tar gzip && \
    wget -q https://github.com/gohugoio/hugo/releases/download/v0.146.0/hugo_extended_0.146.0_linux-amd64.tar.gz && \
    tar -xzf hugo_extended_0.146.0_linux-amd64.tar.gz && \
    mv /tmp/hugo /usr/local/bin/ && \
    chmod +x /usr/local/bin/hugo && \
    /usr/local/bin/hugo version

WORKDIR /src

COPY . .

# Build static site
RUN /usr/local/bin/hugo --minify

# Production stage
FROM nginx:alpine

# Copy built site from builder
COPY --from=builder /src/public /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80


CMD ["nginx", "-g", "daemon off;"]