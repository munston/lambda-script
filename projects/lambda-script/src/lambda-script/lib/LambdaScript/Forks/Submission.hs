{-# LANGUAGE OverloadedStrings #-}

-- | Submission records (ported from scripts/forks/submission_object.py).
-- Records the candidate's intent under .forks/submissions/<agent>.json:
-- the target ref, ahead/behind, and changed files. Part of the lifecycle's
-- recorded state (lane -> submission -> candidate -> receipt).
module LambdaScript.Forks.Submission
  ( writeSubmission
  ) where

import Data.Aeson (encode, object, (.=))
import qualified Data.ByteString.Lazy as BL
import System.Directory (createDirectoryIfMissing)
import System.FilePath (takeDirectory)

import LambdaScript.Forks.Git (forksPath, normalizeAgent)

-- | Write the submission record for a candidate land.
writeSubmission
  :: FilePath            -- ^ repo root
  -> String              -- ^ agent
  -> String              -- ^ target ref
  -> [(String, String)]  -- ^ changed files as (status, path)
  -> Int                 -- ^ ahead
  -> Int                 -- ^ behind
  -> IO ()
writeSubmission root agent targetRef changed ahead behind = do
  let path = forksPath root ["submissions", normalizeAgent agent ++ ".json"]
      val =
        object
          [ "format" .= ("LS_FORK_SUBMISSION_V1" :: String)
          , "agent" .= normalizeAgent agent
          , "target_ref" .= targetRef
          , "ahead" .= ahead
          , "behind" .= behind
          , "changed_files" .= [ object ["path" .= p, "status" .= s] | (s, p) <- changed ]
          ]
  createDirectoryIfMissing True (takeDirectory path)
  BL.writeFile path (encode val)
