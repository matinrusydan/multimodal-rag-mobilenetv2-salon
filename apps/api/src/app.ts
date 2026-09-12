import cookieParser from 'cookie-parser';
import cors from 'cors';
import express from 'express';
import helmet from 'helmet';
import pinoHttp from 'pino-http';
import { env } from './config/env';
import { logger } from './config/logger';
import { errorHandler } from './middleware/errorHandler';
import routes from './routes';
import { initCvService } from './services/CvService';

export function createApp() {
  const app = express();
  initCvService();

  app.use(
    helmet({
      crossOriginResourcePolicy: { policy: 'cross-origin' },
    }),
  );
  app.use(
    cors({
      origin: env.CORS_ORIGIN.split(','),
      credentials: true,
    }),
  );
  app.use(pinoHttp({ logger }));
  app.use(express.json({ limit: '5mb' }));
  app.use(cookieParser());

  app.use(routes);

  app.use(errorHandler);

  return app;
}
