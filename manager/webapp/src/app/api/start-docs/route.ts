import { spawn } from 'child_process';
import { NextResponse } from 'next/server';

export async function POST() {
  try {
    const docsPath = 'C:\\Users\\Sivasai\\Documents\\GitHub\\CaseFarm\\documentation';
    
    // Check if MkDocs is already running
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);
      
      const response = await fetch('http://localhost:8000', {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (response.ok) {
        return NextResponse.json(
          { message: 'MkDocs is already running' }, 
          { status: 200 }
        );
      }
    } catch (error) {
      console.log('MkDocs not running, starting it...');
    }

    // Start MkDocs and keep the command prompt window open
    const child = spawn(`cd /d "${docsPath}" && mkdocs serve`, {
      shell: true,
      stdio: 'inherit',
      env: {
        ...process.env,
        PATH: process.env.PATH
      }
    });


    // Handle spawn errors
    child.on('error', (error) => {
      console.error('Failed to start MkDocs:', error);
      throw new Error(`Spawn error: ${error.message}`);
    });

    // Wait for MkDocs to start
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Check if server started
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      
      const response = await fetch('http://localhost:8000', {
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (response.ok) {
        return NextResponse.json(
          { message: 'MkDocs started successfully', url: 'http://localhost:8000' }, 
          { status: 200 }
        );
      } else {
        throw new Error('Server not responding');
      }
    } catch (error) {
      return NextResponse.json(
        { 
          message: 'MkDocs may be starting. Try opening http://localhost:8000 manually.',
          note: 'If Chrome blocks it, try the solutions mentioned above.',
          details: error instanceof Error ? error.message : 'Unknown error'
        }, 
        { status: 202 }
      );
    }

  } catch (error) {
    console.error('Error starting MkDocs:', error);
    
    return NextResponse.json(
      { 
        error: 'Failed to start MkDocs', 
        details: error instanceof Error ? error.message : 'Unknown error',
        suggestions: [
          'Ensure MkDocs is installed: pip install mkdocs',
          'Check if Python is in your PATH',
          'Try running the command manually in terminal'
        ]
      }, 
      { status: 500 }
    );
  }
}
