-- | Forks command surface for the LambdaScript exe (the Haskell port of the
-- scripts/forks Python tooling). Exposes the JSON-patch landing lifecycle:
-- status, land-json (to main), gadget-land (to a gadget integration branch),
-- gadget-promote (integration -> main), and amalgamate (lane merge).
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
import qualified Data.Map as Map
import System.Directory (doesFileExist)
import System.FilePath ((</>))

import LambdaScript.Forks.Amalgamate (amalgamateGadget)
import LambdaScript.Forks.Gadget (gadgetLand, gadgetPromote)
import LambdaScript.Forks.Git
  ( agentBranch, agents, aheadBehind, classify, fetch, mainRef
  , refExists, repoRoot, shortCommit )
import LambdaScript.Forks.Land (landJson)
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

usage :: String
usage =
  unlines
    [ "forks status"
    , "forks land-json <agent> <patch.json>"
    , "forks gadget-land <gizmo> <gadget> <agent> <patch.json> [--profile <name>]"
    , "forks gadget-promote <gizmo> <gadget> [--profile <name>]"
    , "forks amalgamate <gizmo> <gadget> [--apply] [--profile <name>]"
    , ""
    , "verification commands come from the gizmo manifest verification_profiles (default quick)"
    ]
