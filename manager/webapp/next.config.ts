import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* your other config options */
  
  // Keep existing webpack config for non-Turbopack builds
  webpack: (config) => {
    config.module.rules.push({
      test: /\.ya?ml$/,
      type: 'json',
      use: 'js-yaml-loader'
    });
    
    return config;
  },
  
  // Add Turbopack configuration
  turbopack: {
    // Configure loaders for YAML files
    rules: {
      // For .yaml files
      '*.yaml': {
        loaders: ['js-yaml-loader'],
        as: '*.json',
      },
      // For .yml files
      '*.yml': {
        loaders: ['js-yaml-loader'],
        as: '*.json',
      }
    }
  }
};

export default nextConfig;
