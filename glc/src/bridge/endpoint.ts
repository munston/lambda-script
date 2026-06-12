export type EndpointKind = 'source' | 'host' | 'foreign';

export interface BridgeEndpoint {
  kind: EndpointKind;
  id: string;
  // Future: capabilities, metadata, etc.
}
