import { cn } from '@/lib/utils';

type TagTone = 'green' | 'red' | 'blue' | 'cyan' | 'magenta' | 'slate';

type TagProps = {
  children: React.ReactNode;
  tone?: TagTone;
  className?: string;
};

export function Tag({ children, tone = 'slate', className }: TagProps) {
  return <span className={cn('admin-tag', `admin-tag--${tone}`, className)}>{children}</span>;
}
