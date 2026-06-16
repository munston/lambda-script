module Audio.Features
  ( featureNames
  , extractFeatures
  , featureLine
  ) where

import Data.List (foldl')
import Data.WAVE

featureNames :: [String]
featureNames =
  [ "duration"
  , "channels"
  , "frameRate"
  , "peak"
  , "rms"
  , "meanAbs"
  , "zcr"
  , "crest"
  ] ++ map (("segRms" ++) . show) [(0 :: Int)..7]
    ++ map (("band" ++) . show) ([125,250,500,1000,2000,4000] :: [Int])

extractFeatures :: WAVE -> [Double]
extractFeatures (WAVE hd frames) =
  let mono = map frameMean frames
      n = length mono
      nD = fromIntegral (max 1 n)
      rate = waveFrameRate hd
      rateD = fromIntegral rate
      peak = foldl' max 0 (map abs mono)
      sq = foldl' (\a x -> a + x * x) 0 mono
      rms = sqrt (sq / nD)
      meanAbs = foldl' (\a x -> a + abs x) 0 mono / nD
      zcr = zeroCrossRate mono
      crest = if rms <= epsilon then 0 else peak / rms
      duration = if rate <= 0 then 0 else fromIntegral n / rateD
      base = [duration, fromIntegral (waveNumChannels hd), rateD, peak, rms, meanAbs, zcr, crest]
      segs = segmentRms 8 mono
      bands = map (\f -> log (1 + goertzelPower rateD (fromIntegral f) mono)) ([125,250,500,1000,2000,4000] :: [Int])
  in base ++ segs ++ bands

featureLine :: WAVE -> String
featureLine wav = unwords (zipWith (\n v -> n ++ "=" ++ show v) featureNames (extractFeatures wav))

frameMean :: [WAVESample] -> Double
frameMean [] = 0
frameMean xs = sum (map sampleToDouble xs) / fromIntegral (length xs)

zeroCrossRate :: [Double] -> Double
zeroCrossRate xs =
  case xs of
    [] -> 0
    [_] -> 0
    _ -> let pairs = zip xs (tail xs)
             crosses = length [() | (a,b) <- pairs, signumZ a /= signumZ b]
         in fromIntegral crosses / fromIntegral (length xs - 1)

signumZ :: Double -> Int
signumZ x
  | x >= 0 = 1
  | otherwise = -1

segmentRms :: Int -> [Double] -> [Double]
segmentRms k xs =
  let n = length xs
      empty = replicate k (0 :: Double, 0 :: Int)
      add acc (i,x) = updateAt (bucket n k i) (\(s,c) -> (s + x * x, c + 1)) acc
      stats = foldl' add empty (zip [0..] xs)
  in map (\(s,c) -> if c == 0 then 0 else sqrt (s / fromIntegral c)) stats

bucket :: Int -> Int -> Int -> Int
bucket n k i
  | n <= 0 = 0
  | otherwise = min (k - 1) ((i * k) `div` n)

updateAt :: Int -> (a -> a) -> [a] -> [a]
updateAt _ _ [] = []
updateAt 0 f (x:xs) = f x : xs
updateAt n f (x:xs) = x : updateAt (n - 1) f xs

goertzelPower :: Double -> Double -> [Double] -> Double
goertzelPower rate freq xs
  | rate <= 0 || freq <= 0 || freq >= rate / 2 || null xs = 0
  | otherwise =
      let omega = 2 * pi * freq / rate
          coeff = 2 * cos omega
          step (q1,q2) x = let q0 = coeff * q1 - q2 + x in (q0,q1)
          (s1,s2) = foldl' step (0,0) xs
          power = s1 * s1 + s2 * s2 - coeff * s1 * s2
          n = fromIntegral (length xs)
      in max 0 (power / (n * n))

epsilon :: Double
epsilon = 1.0e-12
