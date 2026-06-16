{-# LANGUAGE OverloadedStrings #-}

-- | LS_MAIN_HISTORY_V1 receipts (ported from scripts/forks/main_history.py).
-- A receipt binds a promotion/land to content: version + source head/tree +
-- changed files + metadata. Written under docs/forks/main-history/patches/.
module LambdaScript.Forks.MainHistory
  ( stampMainVersion
  ) where

import Data.Aeson (Value, encode, object, (.=))
import qualified Data.Aeson.Key as K
import qualified Data.ByteString.Lazy as BL
import Data.List (isPrefixOf, isSuffixOf)
import System.Directory (createDirectoryIfMissing, doesDirectoryExist, listDirectory)
import System.FilePath ((</>))

import LambdaScript.Forks.Git (commit, gitText, treeHash)

mainHistoryDir :: FilePath -> FilePath
mainHistoryDir root = root </> "docs" </> "forks" </> "main-history"

nextNumber :: FilePath -> IO Int
nextNumber root = do
  let pdir = mainHistoryDir root </> "patches"
  exists <- doesDirectoryExist pdir
  if not exists
    then pure 1
    else do
      entries <- listDirectory pdir
      let nums =
            [ n
            | e <- entries
            , "main-" `isPrefixOf` e
            , ".json" `isSuffixOf` e
            , let digits = takeWhile (/= '.') (drop (length ("main-" :: String)) e)
            , [(n, "")] <- [reads digits :: [(Int, String)]]
            ]
      pure (if null nums then 1 else maximum nums + 1)

pad6 :: Int -> String
pad6 n =
  let s = show n
  in replicate (max 0 (6 - length s)) '0' ++ s

-- | Stamp a content-bound receipt; returns the version string (e.g. "main-000002").
stampMainVersion
  :: FilePath            -- ^ repo root
  -> String              -- ^ kind (e.g. "gadget_promotion", "json_patch")
  -> String              -- ^ agent
  -> String              -- ^ title
  -> String              -- ^ base ref
  -> String              -- ^ source ref (the content being recorded)
  -> [(String, String)]  -- ^ changed files as (status, path)
  -> [(String, Value)]   -- ^ metadata
  -> IO String
stampMainVersion root kind agent title baseRef sourceRef changed metadata = do
  n <- nextNumber root
  let version = "main-" ++ pad6 n
  createdAt <- gitText root ["show", "-s", "--format=%cI", sourceRef] ""
  srcHead <- commit root sourceRef
  srcTree <- treeHash root sourceRef
  baseCommit <- commit root baseRef
  let receipt =
        object
          [ "format" .= ("LS_MAIN_HISTORY_V1" :: String)
          , "version" .= version
          , "number" .= n
          , "kind" .= kind
          , "agent" .= agent
          , "title" .= title
          , "base_ref" .= baseRef
          , "base_commit" .= baseCommit
          , "source_ref" .= sourceRef
          , "source_head_before_receipt" .= srcHead
          , "source_tree_before_receipt" .= srcTree
          , "created_at" .= createdAt
          , "changed_files" .= [ object ["path" .= p, "status" .= s] | (s, p) <- changed ]
          , "metadata" .= object [ K.fromString k .= v | (k, v) <- metadata ]
          ]
      pdir = mainHistoryDir root </> "patches"
  createDirectoryIfMissing True pdir
  BL.writeFile (pdir </> (version ++ ".json")) (encode receipt)
  pure version
