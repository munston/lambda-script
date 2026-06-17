{-# LANGUAGE OverloadedStrings #-}

module LambdaScript.Sandbox.Config
  ( SandboxConfig(..)
  , TargetButton(..)
  , cfgToolRoot
  , cfgButton
  , loadConfig
  ) where

import Data.Aeson ((.:), withObject, eitherDecodeFileStrict')
import Data.Aeson.Types (FromJSON(..), Parser)
import qualified Data.Text as T
import System.Directory (doesFileExist)
import System.FilePath ((</>))

data SandboxConfig =
  SandboxConfig FilePath TargetButton
  deriving (Eq, Show)

newtype TargetButton =
  TargetButton String
  deriving (Eq, Show)

cfgToolRoot :: SandboxConfig -> FilePath
cfgToolRoot (SandboxConfig root _) = root

cfgButton :: SandboxConfig -> String
cfgButton (SandboxConfig _ (TargetButton button)) = button

instance FromJSON SandboxConfig where
  parseJSON = withObject "SandboxConfig" $ \o -> do
    root <- requireText "tool_root" =<< o .: "tool_root"
    button <- requireText "button" =<< o .: "button"
    pure (SandboxConfig root (TargetButton button))

requireText :: String -> T.Text -> Parser String
requireText name raw =
  let value = T.unpack raw
  in if null value
       then fail (name ++ " must not be empty")
       else pure value

loadConfig :: FilePath -> IO SandboxConfig
loadConfig cwd = do
  let path = cwd </> "sandbox.json"
  exists <- doesFileExist path
  if exists
    then either (ioError . userError . ("sandbox.json parse failed: " ++)) pure =<< eitherDecodeFileStrict' path
    else ioError (userError "missing sandbox.json in current directory")
