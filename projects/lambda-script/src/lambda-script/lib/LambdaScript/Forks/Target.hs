module LambdaScript.Forks.Target
  ( Agent
  , Gizmo
  , Gadget
  , Target(..)
  , ResolvedTarget
  , mkAgent
  , mkGizmo
  , mkGadget
  , agentName
  , gizmoName
  , gadgetName
  , resolvedIntegrationRef
  , resolvedLaneRef
  , resolveTarget
  ) where

import Data.Char (isAlphaNum)

newtype Agent =
  Agent String
  deriving (Eq, Show)

newtype Gizmo =
  Gizmo String
  deriving (Eq, Show)

newtype Gadget =
  Gadget String
  deriving (Eq, Show)

data Target
  = GadgetTarget Gizmo Gadget
  | RepositoryTarget
  deriving (Eq, Show)

data ResolvedTarget =
  ResolvedTarget String String
  deriving (Eq, Show)

mkAgent :: String -> Either String Agent
mkAgent value = Agent <$> cleanName "agent" value

mkGizmo :: String -> Either String Gizmo
mkGizmo value = Gizmo <$> cleanName "gizmo" value

mkGadget :: String -> Either String Gadget
mkGadget value = Gadget <$> cleanName "gadget" value

agentName :: Agent -> String
agentName (Agent value) = value

gizmoName :: Gizmo -> String
gizmoName (Gizmo value) = value

gadgetName :: Gadget -> String
gadgetName (Gadget value) = value

resolvedIntegrationRef :: ResolvedTarget -> String
resolvedIntegrationRef (ResolvedTarget integration _) = integration

resolvedLaneRef :: ResolvedTarget -> String
resolvedLaneRef (ResolvedTarget _ lane) = lane

resolveTarget :: Agent -> Target -> Either String ResolvedTarget
resolveTarget agent target =
  case target of
    GadgetTarget gizmo gadget ->
      let g = gizmoName gizmo
          x = gadgetName gadget
          a = agentName agent
      in Right (ResolvedTarget
           ("origin/gadgets/" ++ g ++ "/" ++ x ++ "/main")
           ("gadget-agents/" ++ g ++ "/" ++ x ++ "/" ++ a))
    RepositoryTarget ->
      Right (ResolvedTarget "origin/main" ("agents/" ++ agentName agent))

cleanName :: String -> String -> Either String String
cleanName kind raw
  | null raw = Left (kind ++ " name must not be empty")
  | raw == "." || raw == ".." = Left (kind ++ " name is unsafe: " ++ raw)
  | any (`elem` ("/\\:" :: String)) raw = Left (kind ++ " name contains a path separator or drive prefix: " ++ raw)
  | any (not . allowed) raw = Left (kind ++ " name contains unsupported characters: " ++ raw)
  | otherwise = Right raw

allowed :: Char -> Bool
allowed c = isAlphaNum c || c `elem` ("._-" :: String)
