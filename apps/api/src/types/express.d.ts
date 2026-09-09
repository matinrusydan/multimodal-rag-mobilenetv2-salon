declare global {
  namespace Express {
    interface Request {
      auth: {
        userId: number;
        name: string;
        email: string;
        type: number;
        permissions: string[];
        roles: string[];
      };
    }
  }
}

export {};
