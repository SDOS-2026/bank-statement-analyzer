import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const apiUrl = process.env.NG_APP_API_URL || 'http://localhost:8080';
const outputPath = resolve('src/environments/environment.generated.ts');

const contents = `export const generatedEnvironment = {
  apiUrl: '${apiUrl}'
};
`;

writeFileSync(outputPath, contents, 'utf8');
console.log(`[finparse] wrote ${outputPath} with apiUrl=${apiUrl}`);
