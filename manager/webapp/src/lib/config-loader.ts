import * as fs from 'fs';
import * as yaml from 'js-yaml';
import path from 'path';

export function loadConfig() {
  try {
    // Using the absolute path to your YAML file
    const configPath = 'C:/Users/Sivasai/Documents/GitHub/CaseFarm/config.yaml';
    const fileContents = fs.readFileSync(configPath, 'utf8');
    
    // Parse the YAML content into a JavaScript object
    const config = yaml.load(fileContents);
    
    return config;
  } catch (error) {
    console.error('Error loading YAML config:', error);
    
    // Return default configuration in case of error
    return {
      STEAM_ITEMS_LISTER_MULTIPLIER: 1,
      MAX_CLEANUP_ATTEMPTS: 5,
      INITIAL_CLEANUP_PRICE_MULTIPLIER: 0.985,
      CLEANUP_PRICE_DECREMENT: 0.02,
      ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS: 10,
      MAX_ITEMS_LIMIT: 0,
      SELLING_TIME_WAIT: 25
    };
  }
}
