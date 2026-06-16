{-# LANGUAGE OverloadedStrings #-}

-- | LS_JSON_PATCH_V1 model + application (ported from scripts/forks/import_json_patch.py).
-- A JSON patch is a commit message plus full-file operations; it is replayed into
-- a candidate worktree built on the current target ref.
module LambdaScript.Forks.Patch
  ( Patch(..)
  , PatchFile(..)
  , loadPatch
  , applyPatch
  ) where

import Data.Aeson (FromJSON(..), eitherDecodeFileStrict', withObject, (.:), (.:?), (.!=))
import System.Directory (createDirectoryIfMissing, doesFileExist, removeFile)
import System.FilePath ((</>), takeDirectory)

data PatchFile =
  PatchFile
    { pfPath :: FilePath
    , pfAction :: String      -- "replace" | "write" | "delete"
    , pfContent :: Maybe String
    }
  deriving (Eq, Show)

data Patch =
  Patch
    { patchMessage :: String
    , patchFiles :: [PatchFile]
    }
  deriving (Eq, Show)

instance FromJSON PatchFile where
  parseJSON =
    withObject "PatchFile" $ \o ->
      PatchFile
        <$> o .: "path"
        <*> (o .:? "action" .!= "replace")
        <*> o .:? "content"

instance FromJSON Patch where
  parseJSON =
    withObject "Patch" $ \o ->
      Patch
        <$> (o .:? "commit_message" .!= "")
        <*> o .: "files"

-- | Load and decode an LS_JSON_PATCH_V1 file.
loadPatch :: FilePath -> IO (Either String Patch)
loadPatch = eitherDecodeFileStrict'

-- | Apply every file operation into the candidate worktree.
applyPatch :: FilePath -> Patch -> IO ()
applyPatch work patch = mapM_ applyOne (patchFiles patch)
  where
    applyOne (PatchFile path action mContent) = do
      let full = work </> path
      case action of
        "delete" -> do
          exists <- doesFileExist full
          if exists then removeFile full else pure ()
        _ -> do
          createDirectoryIfMissing True (takeDirectory full)
          writeFile full (maybe "" id mContent)
