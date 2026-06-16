module LambdaScript.Bridge.Endpoint where

data EndpointKind
  = EndpointSource
  | EndpointHost
  | EndpointForeign
  deriving (Eq, Show, Read)

data BridgeEndpoint = BridgeEndpoint
  { bridgeEndpointKind :: EndpointKind
  , bridgeEndpointId :: String
  } deriving (Eq, Show, Read)