import { createApp } from './app';
import { env } from './config/env';
import { logger } from './config/logger';

const app = createApp();

app.listen(env.PORT, env.HOST, () => {
  logger.info(`API berjalan di http://${env.HOST}:${env.PORT}`);
});
