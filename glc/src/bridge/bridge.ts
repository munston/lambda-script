import { EndpointKind, BridgeEndpoint } from './endpoint';
import { Program } from '../core/program';

export interface BaseMessage {
  from: EndpointKind;
  to: EndpointKind;
}

export interface SourceToHostMessage extends BaseMessage {
  from: 'source';
  to: 'host';
  payload: Program;
}

export type BridgeMessage = SourceToHostMessage;


export interface BridgeRoute {
  from: EndpointKind;
  to: EndpointKind;
}

export interface BridgeResult {
  success: boolean;
  data?: unknown;
  error?: string;
}

/**
 * Basic message router stub.
 * Validates that the message is compatible with the route and returns a structured result.
 * This is intentionally minimal — real routing logic will be added later.
 */
export function routeMessage(route: BridgeRoute, message: BridgeMessage): BridgeResult {
  if (route.from !== message.from || route.to !== message.to) {
    return {
      success: false,
      error: `Route mismatch: expected ${route.from}→${route.to}, got ${message.from}→${message.to}`,
    };
  }

  // Placeholder for actual routing / transformation logic
  return {
    success: true,
    data: {
      routed: true,
      from: message.from,
      to: message.to,
      payload: message.payload,
    },
  };
}
