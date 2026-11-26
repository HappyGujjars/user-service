import os

flaws = """import { Injectable } from '@nestjs/common';
import * as crypto from 'crypto';
import * as fs from 'fs';
import { exec } from 'child_process';

@Injectable()
export class SecurityFlawsService {
"""

methods = []

# 1. 200 Insecure Hashing methods (MD5 / SHA1) -> CWE-327 / SonarQube S4790
for i in range(1, 101):
    methods.append(f"""  // CWE-327: Use of Weak Hash MD5 #{i}
  hashPasswordVulnerable_{i}(input: string): string {{
    return crypto.createHash('md5').update(input + '{i}').digest('hex');
  }}""")

for i in range(1, 101):
    methods.append(f"""  // CWE-327: Use of Weak Hash SHA1 #{i}
  hashTokenSha1_{i}(token: string): string {{
    return crypto.createHash('sha1').update(token + '{i}').digest('hex');
  }}""")

# 2. 100 Command Injection methods -> CWE-78 / SonarQube S2076
for i in range(1, 101):
    methods.append(f"""  // CWE-78: Command Injection #{i}
  runUserDiagnostic_{i}(cmd: string): void {{
    exec('ping -c 1 ' + cmd, (err, stdout) => {{
      console.log('Result {i}: ' + stdout);
    }});
  }}""")

# 3. 100 Code Injection methods (eval) -> CWE-95 / SonarQube S1523
for i in range(1, 101):
    methods.append(f"""  // CWE-95: Code Injection #{i}
  executeDynamicCode_{i}(userCode: string): any {{
    return eval(userCode + '; // {i}');
  }}""")

# 4. 150 Insecure PRNG methods -> CWE-330 / SonarQube S2245
for i in range(1, 151):
    methods.append(f"""  // CWE-330: Insecure Pseudo-Random Number Generator #{i}
  generateSessionId_{i}(): number {{
    return Math.random() * {i} * 10000;
  }}""")

# 5. 100 Path Traversal methods -> CWE-22 / SonarQube S2083
for i in range(1, 101):
    methods.append(f"""  // CWE-22: Path Traversal #{i}
  readUserDataFile_{i}(userPath: string): string {{
    try {{
      return fs.readFileSync('/tmp/data/' + userPath + '{i}', 'utf8');
    }} catch (e) {{
      return '';
    }}
  }}""")

# 6. 100 Insecure Cipher methods (DES / Blowfish) -> CWE-327 / SonarQube S5147
for i in range(1, 101):
    methods.append(f"""  // CWE-327: Weak Encryption Cipher #{i}
  encryptLegacyData_{i}(data: string): string {{
    try {{
      const cipher = crypto.createCipheriv('des-ecb', Buffer.from('8bytekey'), null);
      return cipher.update(data, 'utf8', 'hex') + cipher.final('hex');
    }} catch (e) {{
      return '';
    }}
  }}""")

# 7. 100 ReDoS methods -> CWE-1333 / SonarQube S5852
for i in range(1, 101):
    methods.append(f"""  // CWE-1333: Inefficient Regular Expression Complexity #{i}
  validateComplexEmail_{i}(email: string): boolean {{
    const regex = new RegExp('^([a-zA-Z0-9_.-]+)+@company{i}([a-zA-Z0-9_.-]+)+$');
    return regex.test(email);
  }}""")

# 8. 50 Hardcoded Credentials -> CWE-798 / SonarQube S2068
for i in range(1, 51):
    methods.append(f"""  // CWE-798: Hardcoded Credential #{i}
  getInternalSecret_{i}(): string {{
    const dbPassword_{i} = 'SuperSecretDbPassword_{i}_!@#';
    return dbPassword_{i};
  }}""")

# 9. 50 SQL Injection methods -> CWE-89 / SonarQube S2077
for i in range(1, 51):
    methods.append(f"""  // CWE-89: SQL Injection raw query concatenation #{i}
  buildUserQuery_{i}(userId: string): string {{
    const sql = "SELECT * FROM users WHERE id = '" + userId + "' AND tenant = '{i}'";
    return sql;
  }}""")

# 10. 50 Open Redirect methods -> CWE-601
for i in range(1, 51):
    methods.append(f"""  // CWE-601: Potential Open Redirect URL construction #{i}
  constructRedirectUrl_{i}(target: string): string {{
    const url = "http://" + target + "/login?serviceId={i}";
    return url;
  }}""")

flaws += "\n\n".join(methods)
flaws += "\n}\n"

with open("src/security-flaws.service.ts", "w") as f:
    f.write(flaws)

print(f"Generated {len(methods)} vulnerable methods successfully!")
