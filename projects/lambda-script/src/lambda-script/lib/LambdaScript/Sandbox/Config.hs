{-# LANGUAGE OverloadedStrings #-}

module LambdaScript.Sandbox.Config
  ( SandboxConfig(..)
  , TargetButton(..)
  , cfgToolRoot
  , cfgButton
  , cfgHatRoot
  , cfgOnepushHat
  , cfgLandHat
  , loadConfig
  ) where

import Data.Aeson ((.:), (.:?), withObject, eitherDecodeFileStrict')
import Data.Aeson.Types (FromJSON(..), Parser)
import qualified Data.Text as T
import System.Directory (doesFileExist)
import System.FilePath ((</>))

data SandboxConfig =
  SandboxConfig FilePath TargetButton (Maybe FilePath) (Maybe FilePath) (Maybe FilePath)
  deriving (Eq, Show)

newtype TargetButton =
  TargetButton String
  deriving (Eq, Show)

cfgToolRoot :: SandboxConfig -> FilePath
cfgToolRoot (SandboxConfig root _ _ _ _) = root

cfgButton :: SandboxConfig -> String
cfgButton (SandboxConfig _ (TargetButton button) _ _ _) = button

cfgHatRoot :: SandboxConfig -> FilePath
cfgHatRoot cfg@(SandboxConfig _ _ hatRoot _ _) =
  case hatRoot of
    Just root -> root
    Nothing -> cfgToolRoot cfg </> "hat"

cfgOnepushHat :: SandboxConfig -> FilePath
cfgOnepushHat cfg@(SandboxConfig _ _ _ onepushHat _) =
  case onepushHat of
    Just path -> path
    Nothing -> cfgToolRoot cfg </> ("onepush-" ++ cfgButton cfg ++ ".hat")

cfgLandHat :: SandboxConfig -> FilePath
cfgLandHat cfg@(SandboxConfig _ _ _ _ landHat) =
  case landHat of
    Just path -> path
    Nothing -> cfgToolRoot cfg </> "land-anything.hat"

instance FromJSON SandboxConfig where
  parseJSON = withObject "SandboxConfig" $ \o -> do
    root <- requireText "tool_root" =<< o .: "tool_root"
    button <- requireText "button" =<< o .: "button"
    hatRoot <- optionalText =<< o .:? "hat_root"
    onepushHat <- optionalText =<< o .:? "onepush_hat"
    landHat <- optionalText =<< o .:? "land_hat"
    pure (SandboxConfig root (TargetButton button) hatRoot onepushHat landHat)

requireText :: String -> T.Text -> Parser String
requireText name raw =
  let value = T.unpack raw
  in if null value
       then fail (name ++ " must not be empty")
       else pure value

optionalText :: Maybe T.Text -> Parser (Maybe String)
optionalText Nothing = pure Nothing
optionalText (Just raw) = do
  let value = T.unpack raw
  if null value then pure Nothing else pure (Just value)

loadConfig :: FilePath -> IO SandboxConfig
loadConfig cwd = do
  let path = cwd </> "sandbox.json"
  exists <- doesFileExist path
  if exists
    then either (ioError . userError . ("sandbox.json parse failed: " ++)) pure =<< eitherDecodeFileStrict' path
    else ioError (userError "missing sandbox.json in current directory")
