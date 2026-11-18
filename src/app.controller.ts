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
    return this.appService.hashPasswordInsecure(password);
  }

  @Get('exec')
  runCommand(@Query('cmd') cmd: string): string {
    this.appService.executeUserCommand(cmd);
    return 'Command executed';
  }

  @Get('eval')
  runEval(@Query('code') code: string): any {
    return this.appService.evaluateExpression(code);
  }
}
