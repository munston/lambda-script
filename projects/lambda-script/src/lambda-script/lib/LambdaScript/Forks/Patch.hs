{-# LANGUAGE OverloadedStrings #-}

-- | LS_FORK_JSON_PATCH_V1 model + application
-- (ported from scripts/forks/import_json_patch.py).
--
-- A JSON patch is a language-neutral description of full-file operations
-- (@upsert@/@delete@) plus a title and optional agent. The raw decoded value is
-- retained (@patchValue@) so it can be recorded verbatim into the replay ledger
-- when the patch lands.
module LambdaScript.Forks.Patch
  ( Patch(..)
  , PatchFile(..)
  , jsonFormat
  , loadPatch
  , applyFileOps
  , cleanPath
  ) where

import Control.Monad (unless, when)
import Data.Aeson (Value(..), eitherDecodeFileStrict')
import qualified Data.Aeson.Key as K
import qualified Data.Aeson.KeyMap as KM
import Data.Foldable (toList)
import qualified Data.Text as T
import System.Directory
  ( createDirectoryIfMissing, doesDirectoryExist, doesFileExist, removeFile )
import System.FilePath ((</>), takeDirectory)
import System.IO (IOMode(WriteMode), hPutStr, hSetEncoding, utf8, withFile)

jsonFormat :: String
jsonFormat = "LS_FORK_JSON_PATCH_V1"

data PatchFile =
  PatchFile
    { pfOp :: String           -- "upsert" | "delete"
    , pfPath :: FilePath        -- cleaned, repo-relative, forward slashes
    , pfEncoding :: String      -- only "utf-8" supported for upsert
    , pfContent :: Maybe String
    }
  deriving (Eq, Show)

data Patch =
  Patch
    { patchValue :: Value       -- raw payload, retained for the replay ledger
    , patchAgent :: Maybe String
    , patchTitle :: String
    , patchFiles :: [PatchFile]
    }
  deriving (Eq, Show)

-- decode ----------------------------------------------------------------------

objLookup :: Value -> String -> Maybe Value
objLookup (Object o) k = KM.lookup (K.fromString k) o
objLookup _ _ = Nothing

asString :: Value -> Maybe String
asString (String s) = Just (T.unpack s)
asString _ = Nothing

asArray :: Value -> [Value]
asArray (Array a) = toList a
asArray _ = []

parsePatchFile :: Value -> Either String PatchFile
parsePatchFile v = do
  let op = maybe "upsert" id (objLookup v "op" >>= asString)
  rawPath <- maybe (Left "patch file missing 'path'") Right (objLookup v "path" >>= asString)
  path <- cleanPath rawPath
  let enc = maybe "utf-8" id (objLookup v "encoding" >>= asString)
      content = objLookup v "content" >>= asString
  case op of
    "upsert" -> Right (PatchFile op path enc content)
    "delete" -> Right (PatchFile op path enc content)
    _ -> Left ("unsupported file op: " ++ op)

-- | Decode and validate an LS_FORK_JSON_PATCH_V1 file, keeping the raw value.
loadPatch :: FilePath -> IO (Either String Patch)
loadPatch fp = do
  decoded <- eitherDecodeFileStrict' fp :: IO (Either String Value)
  pure (decoded >>= fromValue)

fromValue :: Value -> Either String Patch
fromValue v =
  case objLookup v "format" >>= asString of
    Nothing -> Left "patch missing 'format'"
    Just fmt
      | fmt /= jsonFormat -> Left ("unexpected patch format: " ++ fmt)
      | otherwise -> do
          files <- mapM parsePatchFile (maybe [] asArray (objLookup v "files"))
          let agent = objLookup v "agent" >>= asString
              title = maybe "" id (objLookup v "title" >>= asString)
          Right (Patch v agent title files)

-- apply -----------------------------------------------------------------------

-- | Apply every file operation into the candidate worktree.
applyFileOps :: FilePath -> Patch -> IO ()
applyFileOps work patch = mapM_ applyOne (patchFiles patch)
  where
    applyOne pf = do
      let full = work </> pfPath pf
      case pfOp pf of
        "delete" -> do
          isDir <- doesDirectoryExist full
          when isDir (ioError (userError ("refusing to delete directory: " ++ pfPath pf)))
          exists <- doesFileExist full
          unless exists (ioError (userError ("delete target missing: " ++ pfPath pf)))
          removeFile full
        "upsert" -> do
          unless (pfEncoding pf == "utf-8")
            (ioError (userError ("unsupported encoding: " ++ pfEncoding pf)))
          createDirectoryIfMissing True (takeDirectory full)
          writeUtf8 full (maybe "" id (pfContent pf))
        other -> ioError (userError ("unsupported file op: " ++ other))

writeUtf8 :: FilePath -> String -> IO ()
writeUtf8 path s = withFile path WriteMode $ \h -> hSetEncoding h utf8 >> hPutStr h s

-- safety ----------------------------------------------------------------------

-- | Reject unsafe patch paths (mirrors import_json_patch.clean_path):
-- no empty, drive/scheme colon, absolute, @.@/@..@ parts, or @.git@ root.
cleanPath :: FilePath -> Either String FilePath
cleanPath raw
  | null raw = Left "empty path"
  | ':' `elem` raw = Left ("path contains ':': " ++ raw)
  | firstCh == '/' || firstCh == '\\' = Left ("absolute path: " ++ raw)
  | any (\p -> p == "." || p == "..") parts = Left ("unsafe path component: " ++ raw)
  | not (null parts) && head parts == ".git" = Left ("refusing .git path: " ++ raw)
  | null parts = Left ("empty path: " ++ raw)
  | otherwise = Right (joinSlash parts)
  where
    firstCh = head raw
    norm = map (\c -> if c == '\\' then '/' else c) raw
    parts = filter (not . null) (splitOn '/' norm)

splitOn :: Char -> String -> [String]
splitOn d s =
  case break (== d) s of
    (a, []) -> [a]
    (a, _ : rest) -> a : splitOn d rest

joinSlash :: [String] -> String
joinSlash [] = ""
joinSlash [x] = x
joinSlash (x : xs) = x ++ "/" ++ joinSlash xs
