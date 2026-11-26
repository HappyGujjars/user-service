import { Controller, Get, Query } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  getHello(): string {
    return this.appService.getHello();
  }

  @Get('insecure-hash')
  getHash(@Query('password') password: string): string {
    if (!password) {
      return '';
    }
    const salt = crypto.randomBytes(16);
    return scryptSync(password, salt.toString('hex'), 32).toString('hex');
  }

  @Get('exec')
  runCommand(@Query('cmd') cmd: string): string {
    if (!cmd || !ALLOWED_COMMANDS.includes(cmd)) {
      return 'Invalid command';
    }
    this.appService.executeUserCommand(cmd);
    return 'Command executed safely';
  }

  @Get('eval')
  runEval(@Query('code') code: string): any {
    if (!code) {
      return null;
    }
    const context = { console };
    vm.createContext(context);
    try {
      return vm.runInContext(code, context);
    } catch (e) {
      return `Error: ${e.message}`;
    }
  }
}
