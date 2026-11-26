import { Controller, Get, Query } from '@nestjs/common';
import { AppService } from './app.service';

@Controller()
export class AppController {
  constructor(private readonly appService: AppService) {}

  @Get()
  getHello(): string {
    return this.appService.getHello();
  }

  @Get('hash')
  getHash(@Query('password') password: string): string {
    if (!password) {
      return '';
    }
    return this.appService.hashPasswordSecure(password);
  }

  @Get('exec-safe')
  runCommandSafe(@Query('cmd') cmd: string): string {
    if (!cmd || !isValidCommand(cmd)) {
      return 'Invalid command';
    }
    this.appService.executeUserCommand(cmd);
    return 'Command executed safely';
  }

  @Get('eval-safe')
  runEvalSafe(@Query('code') code: string): any {
    if (!code) {
      return null;
    }
    try {
      return this.appService.evaluateExpression(code, { sandboxed: true });
    } catch (error) {
      return 'Evaluation failed';
    }
  }
}
