export const MAX_WIDTH: number;
export const QUALITY: number;
export const MAX_BYTES: number;
export function compress(input: string | Buffer): Promise<{ buffer: Buffer; width: number; quality: number }>;
