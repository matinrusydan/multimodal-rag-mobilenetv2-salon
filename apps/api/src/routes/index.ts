import { Router } from 'express';
import agentRoutes from './agent.routes';
import analyzeRoutes from './analyze.routes';
import authRoutes from './auth.routes';
import chatRoutes from './chat.routes';
import healthRoutes from './health.routes';
import knowledgeRoutes from './knowledge.routes';
import menusRoutes from './menus.routes';
import paymentsRoutes from './payments.routes';
import permissionsRoutes from './permissions.routes';
import reservationsRoutes from './reservations.routes';
import rolesRoutes from './roles.routes';
import routesRoutes from './routes.routes';
import servicesRoutes from './services.routes';
import settingsRoutes from './settings.routes';
import usersRoutes from './users.routes';

const router = Router();

router.use('/api', healthRoutes);
router.use('/api/auth', authRoutes);
router.use('/api/services', servicesRoutes);
router.use('/api/settings', settingsRoutes);
router.use('/api/reservations', reservationsRoutes);
router.use('/api/payments', paymentsRoutes);
router.use('/api/analyze', analyzeRoutes);
router.use('/api/chat', chatRoutes);
router.use('/api/agent', agentRoutes);
router.use('/api/knowledge', knowledgeRoutes);
router.use('/api/users', usersRoutes);
router.use('/api/roles', rolesRoutes);
router.use('/api/permissions', permissionsRoutes);
router.use('/api/routes', routesRoutes);
router.use('/api/menus', menusRoutes);

export default router;
