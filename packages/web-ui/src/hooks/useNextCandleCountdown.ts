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
    // eslint-disable-next-line react-hooks/set-state-in-effect -- syncing to the real UTC clock on mount
    setSeconds(secondsToNext15m());
    const id = setInterval(() => setSeconds(secondsToNext15m()), 1000);
    return () => clearInterval(id);
  }, []);

  return seconds;
}
