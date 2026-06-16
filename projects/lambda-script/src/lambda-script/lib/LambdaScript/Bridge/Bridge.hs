module LambdaScript.Bridge.Bridge where

import LambdaScript.Bridge.Endpoint
import LambdaScript.Core.Program

data BridgeRoute = BridgeRoute
  { bridgeRouteFrom :: EndpointKind
  , bridgeRouteTo :: EndpointKind
  } deriving (Eq, Show, Read)

data SourceToHostMessage = SourceToHostMessage
  { sourceToHostPayload :: Program
  } deriving (Eq, Show, Read)

data BridgeRoutedData = BridgeRoutedData
  { bridgeRouted :: Bool
  , bridgeRoutedFrom :: EndpointKind
  , bridgeRoutedTo :: EndpointKind
  , bridgeRoutedPayload :: Program
  } deriving (Eq, Show, Read)

data BridgeResult = BridgeResult
  { bridgeResultSuccess :: Bool
  , bridgeResultData :: Maybe BridgeRoutedData
  , bridgeResultError :: Maybe String
  } deriving (Eq, Show, Read)

routeMessage :: BridgeRoute -> SourceToHostMessage -> BridgeResult
routeMessage route message =
  let fromKind = EndpointSource
      toKind = EndpointHost
  in if bridgeRouteFrom route /= fromKind || bridgeRouteTo route /= toKind
       then
         BridgeResult
           { bridgeResultSuccess = False
           , bridgeResultData = Nothing
           , bridgeResultError =
               Just
                 ( "Route mismatch: expected "
                     ++ showEndpointKind (bridgeRouteFrom route)
                     ++ "->"
                     ++ showEndpointKind (bridgeRouteTo route)
                     ++ ", got "
                     ++ showEndpointKind fromKind
                     ++ "->"
                     ++ showEndpointKind toKind
                 )
           }
       else
         BridgeResult
           { bridgeResultSuccess = True
           , bridgeResultData =
               Just
                 BridgeRoutedData
                   { bridgeRouted = True
                   , bridgeRoutedFrom = fromKind
                   , bridgeRoutedTo = toKind
                   , bridgeRoutedPayload = sourceToHostPayload message
                   }
           , bridgeResultError = Nothing
           }

showEndpointKind :: EndpointKind -> String
showEndpointKind kind = case kind of
  EndpointSource -> "source"
  EndpointHost -> "host"
  EndpointForeign -> "foreign"