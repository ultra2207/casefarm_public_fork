import { NextResponse } from 'next/server';
import * as fs from 'fs';
import * as yaml from 'js-yaml';

export async function GET() {
  try {
    // Use the absolute path to your YAML file
    const configPath = 'C:/Users/Sivasai/Documents/GitHub/CaseFarm/config.yaml';
    const fileContents = fs.readFileSync(configPath, 'utf8');
    
    // Parse the YAML content
    const config = yaml.load(fileContents);
    
    return NextResponse.json(config);
  } catch (error) {
    console.error('Error loading YAML config:', error);
    
    // Return default configuration in case of error
    return NextResponse.json({
      STEAM_ITEMS_LISTER_MULTIPLIER: 1,
      MAX_CLEANUP_ATTEMPTS: 5,
      INITIAL_CLEANUP_PRICE_MULTIPLIER: 0.985,
      CLEANUP_PRICE_DECREMENT: 0.02,
      ACCOUNT_INVENTORY_SEMAPHORE_STEAM_ITEMS: 10,
      MAX_ITEMS_LIMIT: 0,
      SELLING_TIME_WAIT: 25
    }, { status: 500 });
  }
}
