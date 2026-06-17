-- | Forks command surface for the LambdaScript exe (the Haskell port of the
-- scripts/forks Python tooling). Exposes the JSON-patch landing lifecycle:
-- status, land-anything, land-json, gadget-land, gadget-promote, and
-- amalgamate.
--
-- Gadget operations resolve their verification gate from the gizmo manifest's
-- verification_profiles (default "quick"; override with --profile <name>), so
-- forks and gizmo share one verification contract.
-- See docs/forks/AMALGAMATION_STATE_MACHINE.md.
module LambdaScript.Forks
  ( run
  , usage
  ) where

import Control.Monad (forM)
import qualified Data.Aeson as Aeson
import qualified Data.Aeson.Key as Key
import qualified Data.Aeson.KeyMap as KeyMap
import qualified Data.Map as Map
import qualified Data.Text as Text
import System.Directory (doesFileExist)
import System.FilePath ((</>))

import LambdaScript.Forks.Amalgamate (amalgamateGadget)
import LambdaScript.Forks.Gadget (gadgetLand, gadgetPromote)
import LambdaScript.Forks.Git
  ( agentBranch, agents, aheadBehind, classify, fetch, mainRef
  , refExists, repoRoot, shortCommit )
import LambdaScript.Forks.Land (landJson)
import LambdaScript.Forks.Patch (Patch(..), loadPatch, patchAgent, patchValue)
import LambdaScript.Gizmo.Types (GadgetManifest(..), GizmoManifest(..))

-- | Resolve a gadget's verification-profile commands from
-- @examples/gizmos/<gizmo>.gizmo.json@. Falls back to @[]@ (skip) when the
-- manifest, gadget, or named profile is absent.
resolveVerify :: FilePath -> String -> String -> String -> IO [String]
resolveVerify root gizmo gadget profile = do
  let path = root </> "examples" </> "gizmos" </> (gizmo ++ ".gizmo.json")
  exists <- doesFileExist path
  if not exists
    then pure []
    else do
      decoded <- Aeson.eitherDecodeFileStrict' path :: IO (Either String GizmoManifest)
      case decoded of
        Left _ -> pure []
        Right manifest ->
          case Map.lookup gadget (gizmoManifestGadgets manifest) of
            Nothing -> pure []
            Just gm ->
              case gadgetManifestVerificationProfiles gm of
                Nothing -> pure []
                Just profiles -> pure (Map.findWithDefault [] profile profiles)

-- | Pull an optional @--profile <name>@ out of the argument list (default "quick").
extractProfile :: [String] -> (String, [String])
extractProfile = go []
  where
    go acc ("--profile" : name : rest) = (name, reverse acc ++ rest)
    go acc (x : rest) = go (x : acc) rest
    go acc [] = ("quick", reverse acc)

-- | Repository agent-lane status against origin/main (mirrors forks.py cmd_status).
forksStatus :: FilePath -> IO String
forksStatus root = do
  fetch root
  mainShort <- shortCommit root mainRef
  rows <- forM agents $ \agent -> do
    let branch = agentBranch agent
    localExists <- refExists root branch
    remoteExists <- refExists root ("origin/" ++ branch)
    if not (localExists || remoteExists)
      then pure ("  " ++ branch ++ ": (absent)")
      else do
        let ref = if localExists then branch else "origin/" ++ branch
        (ahead, behind) <- aheadBehind root ref mainRef
        hd <- shortCommit root ref
        pure ("  " ++ branch ++ ": " ++ classify ahead behind
               ++ " ahead=" ++ show ahead ++ " behind=" ++ show behind ++ " head=" ++ hd)
  pure (unlines (("main " ++ mainShort) : rows))

run :: [String] -> IO String
run rawArgs =
  let (profile, args) = extractProfile rawArgs
  in case args of
       ["status"] -> repoRoot >>= forksStatus
       ["land-anything", file] -> do
         root <- repoRoot
         landAnything root profile file
       ["land-json", agent, file] -> do
         root <- repoRoot
         landJson root agent mainRef [] file False
       ["gadget-land", gizmo, gadget, agent, file] -> do
         root <- repoRoot
         cmds <- resolveVerify root gizmo gadget profile
         gadgetLand root gizmo gadget agent cmds file
       ["gadget-promote", gizmo, gadget] -> do
         root <- repoRoot
         cmds <- resolveVerify root gizmo gadget profile
         gadgetPromote root gizmo gadget cmds
       ["amalgamate", gizmo, gadget] -> do
         root <- repoRoot
         cmds <- resolveVerify root gizmo gadget profile
         amalgamateGadget root gizmo gadget cmds False
       ["amalgamate", gizmo, gadget, "--apply"] -> do
         root <- repoRoot
         cmds <- resolveVerify root gizmo gadget profile
         amalgamateGadget root gizmo gadget cmds True
       _ -> pure usage

landAnything :: FilePath -> String -> FilePath -> IO String
landAnything root profile file = do
  parsed <- loadPatch file
  patch <- either (ioError . userError . ("patch parse failed: " ++)) pure parsed
  agent <- case patchAgent patch of
    Just a | not (null a) -> pure a
    _ -> ioError (userError "patch missing agent")
  case patchTarget (patchValue patch) of
    Left err -> ioError (userError err)
    Right RepositoryPatchTarget -> landJson root agent mainRef [] file False
    Right (GadgetPatchTarget gizmo gadget) -> do
      cmds <- resolveVerify root gizmo gadget profile
      gadgetLand root gizmo gadget agent cmds file

data PatchTarget
  = RepositoryPatchTarget
  | GadgetPatchTarget String String
  deriving (Eq, Show)

patchTarget :: Aeson.Value -> Either String PatchTarget
patchTarget value =
  case lookupKey "target" value of
    Nothing -> Left "patch missing target object"
    Just target ->
      case valueString "kind" target of
        Just "repository" -> Right RepositoryPatchTarget
        Just "repo" -> Right RepositoryPatchTarget
        Just "ref" -> Right RepositoryPatchTarget
        Just "gadget" -> do
          gizmo <- requiredString "target.gizmo" "gizmo" target
          gadget <- case valueString "gadget" target of
            Just g -> Right g
            Nothing -> requiredString "target.gadget" "lane" target
          Right (GadgetPatchTarget gizmo gadget)
        Just other -> Left ("unsupported target kind: " ++ other)
        Nothing -> Left "target missing kind"

requiredString :: String -> String -> Aeson.Value -> Either String String
requiredString label key value =
  case valueString key value of
    Just s | not (null s) -> Right s
    _ -> Left (label ++ " missing")

valueString :: String -> Aeson.Value -> Maybe String
valueString key value =
  case lookupKey key value of
    Just (Aeson.String s) -> Just (Text.unpack s)
    _ -> Nothing

lookupKey :: String -> Aeson.Value -> Maybe Aeson.Value
lookupKey key (Aeson.Object obj) = KeyMap.lookup (Key.fromString key) obj
lookupKey _ _ = Nothing

usage :: String
usage =
  unlines
    [ "forks status"
    , "forks land-anything <patch.json> [--profile <name>]"
    , "forks land-json <agent> <patch.json>"
    , "forks gadget-land <gizmo> <gadget> <agent> <patch.json> [--profile <name>]"
    , "forks gadget-promote <gizmo> <gadget> [--profile <name>]"
    , "forks amalgamate <gizmo> <gadget> [--apply] [--profile <name>]"
    , ""
    , "verification commands come from the gizmo manifest verification_profiles (default quick)"
    ]
