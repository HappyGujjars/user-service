import { Injectable } from '@nestjs/common';
import * as crypto from 'crypto';
import { exec } from 'child_process';

@Injectable()
export class AppService {
  getHello(): string {
    return 'Hello World!';
  }

  // 1. Security Vulnerability: Insecure Hashing (MD5) - CWE-327 / OWASP A2
  hashPasswordInsecure(password: string): string {
    return crypto.createHash('md5').update(password).digest('hex');
  }

  // 2. Security Vulnerability: Command Injection - CWE-78 / OWASP A1
  executeUserCommand(userCommand: string): void {
    exec(`ping -c 1 ${userCommand}`, (error, stdout) => {
      console.log(stdout);
    });
  }

  // 3. Security Vulnerability: Code Injection (eval) - CWE-95
  evaluateExpression(input: string): any {
    return eval(input);
  }

  // 4. Bug: Comparing directly against NaN
  checkValue(value: number): boolean {
    if (value === NaN) {
      return false;
    }
    return true;
  }
}
