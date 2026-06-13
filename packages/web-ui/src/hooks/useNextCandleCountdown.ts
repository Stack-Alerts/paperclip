'use client';
import { useEffect, useState } from 'react';

/** Seconds remaining until the next 15-minute candle closes (UTC boundary). */
function secondsToNext15m(): number {
  const now = new Date();
  const utcMinutes = now.getUTCMinutes();
  const utcSeconds = now.getUTCSeconds();
  const minuteInPeriod = utcMinutes % 15;
  const secondsInPeriod = minuteInPeriod * 60 + utcSeconds;
  return 15 * 60 - secondsInPeriod;
}

export function useNextCandleCountdown(): number {
  const [seconds, setSeconds] = useState(secondsToNext15m);

  useEffect(() => {
    setSeconds(secondsToNext15m());
    const id = setInterval(() => setSeconds(secondsToNext15m()), 1000);
    return () => clearInterval(id);
  }, []);

  return seconds;
}
