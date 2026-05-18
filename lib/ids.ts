import { customAlphabet } from "nanoid";

const nano = customAlphabet("0123456789abcdefghijklmnopqrstuvwxyz", 10);

export const newId = (prefix: string) => `${prefix}_${nano()}`;

export const intentId = () => newId("intent");
export const capabilityId = () => newId("capability");
export const pathId = () => newId("path");
export const executionId = () => newId("execution");
export const patternId = () => newId("pattern");
export const accountId = () => newId("account");
export const creditEventId = () => newId("credit");
export const nodeAssignmentId = () => newId("assign");
