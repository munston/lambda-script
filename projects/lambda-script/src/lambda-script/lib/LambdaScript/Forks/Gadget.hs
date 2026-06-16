-- | Gadget land + promote (ported from scripts/forks/{gadget_land_json,gadget_promote}.py).
-- Two-stage isolation: agent patch -> gadget integration branch (land), then
-- gadget integration -> repository main (promote), each ahead-only gated.
module LambdaScript.Forks.Gadget
  ( gadgetTargetRef
  , gadgetIntegrationBranch
  , gadgetLand
  , gadgetPromote
  ) where

import Control.Monad (forM_, unless, when)
import Data.Aeson (toJSON)

import LambdaScript.Forks.Git
import LambdaScript.Forks.Land (landJson, shellIn, syncAgent)
import qualified LambdaScript.Forks.MainHistory as MH

-- run the manifest verification commands in a worktree
gadgetVerify :: FilePath -> [String] -> IO ()
gadgetVerify work cmds =
  forM_ cmds $ \cmd -> do
    code <- shellIn work cmd
    when (code /= 0) (ioError (userError ("verification failed: " ++ cmd)))

-- | @origin/gadgets/<gizmo>/<gadget>/main@ — the gadget integration target.
gadgetTargetRef :: String -> String -> String
gadgetTargetRef gizmo gadget = "origin/gadgets/" ++ gizmo ++ "/" ++ gadget ++ "/main"

gadgetIntegrationBranch :: String -> String -> String
gadgetIntegrationBranch gizmo gadget = "gadgets/" ++ gizmo ++ "/" ++ gadget ++ "/main"

-- | Land an agent JSON patch to the gadget integration branch (lane sync deferred to amalgamation).
gadgetLand :: FilePath -> String -> String -> String -> [String] -> FilePath -> IO String
gadgetLand root gizmo gadget agent verifyCmds patchFile =
  landJson root agent (gadgetTargetRef gizmo gadget) verifyCmds patchFile True

-- | Promote a gadget integration branch to repository main (ahead-only gated, verified).
gadgetPromote :: FilePath -> String -> String -> [String] -> IO String
gadgetPromote root gizmo gadget verifyCmds = do
  ensureDirs root
  fetch root
  let target = gadgetTargetRef gizmo gadget
  okM <- refExists root mainRef
  unless okM (ioError (userError ("missing " ++ mainRef)))
  okT <- refExists root target
  unless okT (ioError (userError ("missing " ++ target)))

  (ahead, behind) <- aheadBehind root target mainRef
  when (ahead == 0 && behind == 0) (ioError (userError (target ++ " is already even with " ++ mainRef)))
  when (behind /= 0)
    (ioError (userError (target ++ " is not based on current " ++ mainRef
                          ++ ": ahead=" ++ show ahead ++ " behind=" ++ show behind ++ "; sync/rebase before promotion")))

  let work = forksPath root ["promotions", gizmo ++ "-" ++ gadget]
  _ <- git root ["worktree", "remove", "--force", work]
  _ <- git root ["worktree", "prune"]
  _ <- git root ["worktree", "add", "--detach", work, target]

  gadgetVerify work verifyCmds

  fetch root
  (ahead2, behind2) <- aheadBehind root target mainRef
  when (ahead2 /= ahead || behind2 /= behind)
    (ioError (userError "source/destination relationship changed during verification; rerun promotion"))

  anc <- isAncestor work mainRef "HEAD"
  unless anc (ioError (userError (mainRef ++ " is not an ancestor of promotion candidate")))

  pushRes <- git work ["push", "origin", "HEAD:main"]
  when (gitExit pushRes /= 0) (ioError (userError ("promotion push failed: " ++ gitStderr pushRes)))
  fetch root
  forM_ agents (syncAgent root)
  changed <- changedFiles root target mainRef
  let meta =
        [ ("gizmo", toJSON gizmo)
        , ("gadget", toJSON gadget)
        , ("target_ref", toJSON target)
        , ("promoted_commits", toJSON ahead)
        ]
  version <- MH.stampMainVersion root "gadget_promotion" "system"
               ("Promote " ++ gizmo ++ "/" ++ gadget) mainRef target changed meta
  pure ("promoted " ++ gizmo ++ "/" ++ gadget
         ++ " -> main (promoted_commits=" ++ show ahead ++ ", receipt=" ++ version ++ ")")
