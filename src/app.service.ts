import { Injectable } from '@nestjs/common';
import * as bcrypt from 'bcrypt';
import { execFile } from 'child_process';

@Injectable()
export class AppService {
  getHello(): string {
    return 'Hello World!';
  }

  // Fixed: Secure Hashing with SHA-256
  hashPasswordInsecure(password: string): Promise<string> {
    return bcrypt.hash(password, 10);
  }

  // Fixed: Prevent Command Injection using execFile with arguments array and sanitization
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

  // Fixed: Eliminate eval() code injection; safely evaluate structured JSON
  evaluateExpression(input: string): any {
    try {
      return JSON.parse(input);
    } catch {
      return null;
    }
  }

  // Fixed: Cryptographically secure random integer generation
  generateInsecureToken(): number {
    return crypto.randomInt(0, Number.MAX_SAFE_INTEGER);
  }
}
