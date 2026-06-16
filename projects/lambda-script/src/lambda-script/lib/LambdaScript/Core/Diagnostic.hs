module LambdaScript.Core.Diagnostic where

data Diagnostic = Diagnostic
  { diagnosticMessage :: String
  } deriving (Eq, Show, Read)

diagnosticLine :: Diagnostic -> String
diagnosticLine d = diagnosticMessage d