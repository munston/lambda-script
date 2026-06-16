{-# LANGUAGE OverloadedStrings #-}

-- | Committed replay ledger (ported from scripts/forks/replay_ledger.py).
--
-- When a JSON patch lands, its payload is stored content-addressed and an entry
-- is appended to the per-agent ledger, both written into the candidate worktree
-- so they are committed onto the integration branch. This is what makes an agent
-- lane disposable: the work is preserved (and later audited as materialised)
-- in the ledger, independent of the lane branch.
module LambdaScript.Forks.ReplayLedger
  ( appendEntry
  , gadgetLedgerRelpath
  ) where

import Data.Aeson (Value(..), encode, eitherDecodeFileStrict', object, (.=))
import qualified Data.Aeson.Key as K
import qualified Data.Aeson.KeyMap as KM
import qualified Data.ByteString.Lazy as BL
import Data.Foldable (toList)
import qualified Data.Scientific as Sci
import qualified Data.Text as T
import System.Directory (createDirectoryIfMissing, doesFileExist)
import System.FilePath ((</>), takeDirectory)

import LambdaScript.Forks.Git (normalizeAgent, nowIso)
import LambdaScript.Forks.Hash (jsonSha256, sha256Text)

ledgerRoot :: String
ledgerRoot = "forks/replay-ledger"

payloadRoot :: String
payloadRoot = ledgerRoot ++ "/payloads"

ledgerFormat, entryFormat, payloadFormat :: String
ledgerFormat = "LS_FORK_REPLAY_LEDGER_V1"
entryFormat = "LS_FORK_REPLAY_LEDGER_ENTRY_V1"
payloadFormat = "LS_FORK_REPLAY_PAYLOAD_V1"

-- helpers ---------------------------------------------------------------------

objLookup :: Value -> String -> Maybe Value
objLookup (Object o) k = KM.lookup (K.fromString k) o
objLookup _ _ = Nothing

objStr :: Value -> String -> Maybe String
objStr v k =
  case objLookup v k of
    Just (String s) -> Just (T.unpack s)
    _ -> Nothing

asInt :: Value -> Maybe Int
asInt (Number n) = Sci.toBoundedInteger n
asInt _ = Nothing

asArray :: Maybe Value -> [Value]
asArray (Just (Array a)) = toList a
asArray _ = []

-- collapse path separators / colons into a single token (mirrors safe_token join)
safeToken :: String -> String
safeToken = map (\c -> if c == '/' || c == '\\' || c == ':' then '_' else c)

payloadRelpath :: String -> String
payloadRelpath sha = payloadRoot ++ "/" ++ take 2 sha ++ "/" ++ sha ++ ".json"

-- target descriptor + ledger location ----------------------------------------

targetDescriptor :: Value -> String -> Value
targetDescriptor payload targetRef =
  case objLookup payload "target" of
    Just t@(Object _) ->
      let kind = maybe "gadget" id (objStr t "kind")
          gizmo = objStr t "gizmo"
          gadget = case objStr t "gadget" of
                     Just g -> Just g
                     Nothing -> objStr t "lane"
      in case (kind, gizmo, gadget) of
           ("gadget", Just gz, Just gd) ->
             object ["kind" .= ("gadget" :: String), "gizmo" .= gz, "gadget" .= gd, "target_ref" .= targetRef]
           _ -> refTarget
    _ -> refTarget
  where
    refTarget = object ["kind" .= ("ref" :: String), "target_ref" .= targetRef]

ledgerRelpath :: String -> Value -> String
ledgerRelpath agent target =
  case objStr target "kind" of
    Just "gadget" ->
      gadgetLedgerRelpath (maybe "" id (objStr target "gizmo")) (maybe "" id (objStr target "gadget")) agent
    _ ->
      ledgerRoot ++ "/refs/" ++ safeToken (maybe "unknown" id (objStr target "target_ref")) ++ "/" ++ safeToken agent ++ ".json"

-- | Path of an agent's gadget replay ledger (used by the amalgamate audit too).
gadgetLedgerRelpath :: String -> String -> String -> String
gadgetLedgerRelpath gizmo gadget agent =
  ledgerRoot ++ "/gadgets/" ++ safeToken gizmo ++ "/" ++ safeToken gadget ++ "/" ++ safeToken (normalizeAgent agent) ++ ".json"

-- fingerprints ----------------------------------------------------------------

fileFingerprint :: Value -> Value
fileFingerprint item =
  let op = maybe "upsert" id (objStr item "op")
      path = maybe "" id (objStr item "path")
      base = ["op" .= op, "path" .= path]
  in if op == "upsert"
       then
         let content = maybe "" id (objStr item "content")
             enc = maybe "utf-8" id (objStr item "encoding")
         in object (base ++ [ "encoding" .= enc, "content_sha256" .= sha256Text content, "content_length" .= length content ])
       else object base

-- payload object --------------------------------------------------------------

writePayloadObject :: FilePath -> Value -> String -> IO String
writePayloadObject work payload sha = do
  let relpath = payloadRelpath sha
      path = work </> relpath
  exists <- doesFileExist path
  if exists
    then pure relpath
    else do
      now <- nowIso
      let obj = object ["format" .= payloadFormat, "json_patch_sha256" .= sha, "created_at" .= now, "payload" .= payload]
      createDirectoryIfMissing True (takeDirectory path)
      BL.writeFile path (encode obj)
      pure relpath

-- ledger read -----------------------------------------------------------------

emptyLedger :: String -> Value -> IO Value
emptyLedger agent target = do
  now <- nowIso
  pure $ object
    [ "format" .= ledgerFormat
    , "agent" .= agent
    , "target" .= target
    , "created_at" .= now
    , "updated_at" .= now
    , "next_sequence" .= (1 :: Int)
    , "entries" .= ([] :: [Value])
    ]

readLedger :: FilePath -> String -> Value -> IO Value
readLedger path agent target = do
  exists <- doesFileExist path
  if not exists
    then emptyLedger agent target
    else do
      decoded <- eitherDecodeFileStrict' path :: IO (Either String Value)
      case decoded of
        Right v@(Object _) -> pure v
        _ -> emptyLedger agent target

-- append ----------------------------------------------------------------------

-- | Append a landed JSON patch to its agent ledger (idempotent on json_patch_sha256).
-- Writes the payload object and the ledger into @work@. Returns the ledger relpath.
appendEntry :: FilePath -> String -> Value -> String -> IO String
appendEntry work agent0 payload targetRef = do
  let agent = normalizeAgent agent0
      target = targetDescriptor payload targetRef
      relpath = ledgerRelpath agent target
      path = work </> relpath
      files = asArray (objLookup payload "files")
      fps = map fileFingerprint files
      sha = jsonSha256 payload
      title = maybe "" id (objStr payload "title")
  payloadPath <- writePayloadObject work payload sha
  ledger <- readLedger path agent target
  let entries = asArray (objLookup ledger "entries")
      already = any (\e -> objStr e "json_patch_sha256" == Just sha) entries
  if already
    then pure relpath
    else do
      now <- nowIso
      let nextSeq = maybe (length entries + 1) id (objLookup ledger "next_sequence" >>= asInt)
          entry = object
            [ "format" .= entryFormat
            , "sequence" .= nextSeq
            , "agent" .= agent
            , "target" .= target
            , "title" .= title
            , "json_patch_sha256" .= sha
            , "payload_path" .= payloadPath
            , "file_count" .= length files
            , "file_fingerprints" .= fps
            , "target_ref_at_capture" .= targetRef
            , "created_at" .= now
            ]
          ledger' = object
            [ "format" .= ledgerFormat
            , "agent" .= agent
            , "target" .= target
            , "created_at" .= maybe now id (objStr ledger "created_at")
            , "updated_at" .= now
            , "next_sequence" .= (nextSeq + 1)
            , "entries" .= (entries ++ [entry])
            ]
      createDirectoryIfMissing True (takeDirectory path)
      BL.writeFile path (encode ledger')
      pure relpath
