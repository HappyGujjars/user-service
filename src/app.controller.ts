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
    return this.appService.hashPasswordInsecure(password);
  }

  @Get('exec')
  runCommand(@Query('cmd') cmd: string): string {
    if (!cmd) {
      return 'Command missing';
    }
    this.appService.executeUserCommand(cmd);
    return 'Command executed safely';
  }

  @Get('eval')
  runEval(@Query('code') code: string): any {
    if (!code) {
      return null;
    }
    return this.appService.evaluateExpression(code);
  }
}
