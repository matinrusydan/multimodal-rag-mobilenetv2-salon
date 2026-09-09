import type { BaseRepository } from '../repositories/BaseRepository';

export abstract class BaseService {
  protected repo: BaseRepository | null = null;
}
