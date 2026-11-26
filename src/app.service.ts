import { Injectable } from '@nestjs/common';
import * as crypto from 'crypto';
import { execFile } from 'child_process';

@Injectable()
export class AppService {
  getHello(): string {
    return 'Hello World!';
  }

  // 1. Fixed: Secure Hashing with SHA-256
  hashPasswordInsecure(password: string): string {
    return crypto.createHash('sha256').update(password).digest('hex');
  }

  // 2. Fixed: Prevent Command Injection using execFile with arguments array and sanitization
  executeUserCommand(userCommand: string): void {
    const sanitizedHost = userCommand.replace(/[^a-zA-Z0-9.-]/g, '');
    if (!sanitizedHost) {
      return;
    }
    execFile('ping', ['-c', '1', sanitizedHost], (error, stdout) => {
      if (error) {
        console.error(error.message);
        return;
      }
      console.log(stdout);
    });
  }

  // 3. Fixed: Eliminate eval() code injection; safely evaluate structured JSON
  evaluateExpression(input: string): any {
    try {
      return JSON.parse(input);
    } catch {
      return null;
    }
  }

  // 4. Fixed: Cryptographically secure random integer generation
  generateInsecureToken(): number {
    return crypto.randomInt(0, Number.MAX_SAFE_INTEGER);
  }
}
