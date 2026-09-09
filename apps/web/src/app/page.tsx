'use client';

import { motion, useAnimation } from 'framer-motion';
import { Kalnia } from 'next/font/google';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

const kalnia = Kalnia({ weight: '400', subsets: ['latin'] });

const svgVariants = {
  hidden: { opacity: 1 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0,
    },
  },
};

const elementVariants = {
  hidden: {
    pathLength: 0,
    opacity: 0,
  },
  visible: {
    pathLength: 1,
    opacity: 1,
    transition: {
      duration: 0.85,
      ease: 'easeOut' as const,
    },
  },
};

const logoContainerVariants = {
  assemble: {
    y: -120,
    opacity: 1,
  },
  drop: {
    y: 0,
    opacity: 1,
    transition: {
      type: 'spring' as const,
      damping: 15,
      stiffness: 90,
      delay: 0.15,
    },
  },
  shift: {
    x: 0,
    transition: {
      type: 'tween' as const,
      ease: 'easeOut' as const,
      duration: 0.55,
    },
  },
};

const shadowVariants = {
  assemble: { opacity: 0, scale: 0 },
  drop: {
    opacity: 1,
    scale: 1,
    transition: {
      ease: 'easeOut' as const,
      duration: 0.3,
      delay: 0.35,
    },
  },
  shift: {
    scale: 1,
  },
};

const textVariants = {
  hidden: {
    opacity: 0,
    x: 50,
    width: 0,
  },
  visible: {
    opacity: 1,
    x: 0,
    width: 'auto',
    transition: {
      type: 'tween' as const,
      ease: 'easeOut' as const,
      duration: 0.55,
    },
  },
};

export default function SplashScreen() {
  const router = useRouter();
  const svgControls = useAnimation();
  const logoControls = useAnimation();
  const shadowControls = useAnimation();
  const textControls = useAnimation();

  useEffect(() => {
    let isMounted = true;

    const wait = (duration: number) =>
      new Promise((resolve) => {
        window.setTimeout(resolve, duration);
      });

    const startAnimationSequence = async () => {
      svgControls.start('visible');
      logoControls.start('assemble');
      shadowControls.start('assemble');
      textControls.start('hidden');

      await wait(750);
      if (!isMounted) return;

      logoControls.start('drop');
      shadowControls.start('drop');

      await wait(700);
      if (!isMounted) return;

      logoControls.start('shift');
      textControls.start('visible');
      shadowControls.start('shift');

      await wait(650);
      if (!isMounted) return;

      router.replace('/home');
    };

    startAnimationSequence();

    return () => {
      isMounted = false;
    };
  }, [router, svgControls, logoControls, shadowControls, textControls]);

  return (
    <main
      className="min-h-screen flex justify-center items-center"
      style={{ backgroundColor: 'var(--auth-background)' }}
    >
      <div className="flex items-center gap-3">
        <motion.div
          className="relative"
          variants={logoContainerVariants}
          animate={logoControls}
          initial="assemble"
        >
          <motion.svg
            width="58"
            height="27"
            viewBox="0 0 58 27"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            variants={svgVariants}
            animate={svgControls}
            initial="hidden"
            aria-hidden="true"
          >
            <motion.path
              d="M34.3124 0.0527611C32.5842 0.23066 30.7163 0.789772 28.9754 1.66656C27.5903 2.36545 25.9638 3.61075 23.7655 5.64388C21.2495 7.96928 19.8009 9.02396 17.9203 9.91346C14.9468 11.3239 11.77 11.4764 8.8347 10.3328C7.61482 9.86263 6.71262 9.2654 5.54357 8.13447C4.93363 7.54994 4.70491 7.38475 4.89551 7.66431C5.68335 8.80794 7.41151 10.193 8.89824 10.8665C10.3596 11.5273 11.4269 11.756 13.3584 11.8322C15.4043 11.9085 16.6114 11.7306 18.2125 11.0952C20.1694 10.3201 21.2241 9.58308 24.2611 6.85105C27.4379 4.00467 29.1787 2.78479 31.2246 1.97153C32.94 1.27264 33.7278 1.14557 36.0278 1.14557C37.9339 1.13286 38.2389 1.17099 39.3825 1.48866C42.9151 2.46711 45.6979 4.48753 48.5316 8.12176C50.0818 10.1041 50.8189 10.8284 51.8354 11.3748C52.4835 11.7179 52.7884 11.8068 53.6398 11.8449C55.0122 11.9212 55.7619 11.667 56.6641 10.8411C57.3884 10.1803 57.6807 9.6339 57.8077 8.69358C57.8967 8.07093 57.9221 8.03281 57.3376 9.36706C57.058 10.0151 56.41 10.6759 55.6984 11.0698C55.3807 11.235 54.9995 11.2985 54.1354 11.2985C52.1531 11.2985 51.2763 10.6886 48.9636 7.70243C46.0537 3.97925 43.4742 1.9207 40.2593 0.777066C38.5438 0.154419 36.1803 -0.125138 34.3124 0.0527611Z"
              fill="url(#paint0_linear_20_195)"
              variants={elementVariants}
            />
            <motion.path
              d="M35.7225 4.05542C32.7237 4.67807 30.3475 5.9996 27.069 8.83328C26.0906 9.67195 24.8961 10.625 24.426 10.9427C23.295 11.6924 21.6812 12.3404 20.1564 12.6581C19.0509 12.8868 18.6442 12.9123 15.747 12.836C13.1929 12.7598 12.3288 12.7852 11.3631 12.9377C8.6819 13.3697 6.38192 14.5134 4.3742 16.4067C3.35763 17.3724 3.28139 17.6647 4.28525 16.7625C5.77198 15.4156 8.03384 14.2211 10.0797 13.7001C11.8333 13.2554 13.5487 13.1791 16.0012 13.4587C18.4663 13.7382 20.0801 13.662 21.8464 13.2172C24.121 12.6327 25.6713 11.7178 28.2381 9.44322C30.6905 7.2576 32.4822 6.13938 34.5789 5.47861C38.912 4.10625 43.4103 5.33883 47.2352 8.92223C48.1501 9.77361 48.1501 9.77361 47.718 9.17637C46.5617 7.53716 44.4904 5.809 42.7114 5.00845C40.5131 4.00459 37.743 3.63608 35.7225 4.05542Z"
              fill="url(#paint1_linear_20_195)"
              variants={elementVariants}
            />
            <motion.path
              d="M54.0462 5.8345C53.6269 6.06323 53.1821 6.77483 53.1821 7.21958C53.1821 7.66432 53.4998 8.27426 53.8048 8.43946C54.1987 8.64277 54.6816 8.59194 54.9611 8.31239C55.3296 7.94388 55.2788 7.71515 54.8086 7.6262C53.7921 7.42289 53.5252 6.77483 54.1479 6.03782C54.5164 5.59307 54.5164 5.58036 54.0462 5.8345Z"
              fill="#52002F"
              variants={elementVariants}
            />
            <motion.path
              d="M36.4725 8.89689C34.4393 9.35435 32.6985 10.3328 30.6526 12.2007C28.8101 13.8654 27.9714 14.4753 26.561 15.1742C24.7947 16.0383 23.8162 16.2416 22.0118 16.1526C20.8682 16.0891 20.2201 15.9747 18.7461 15.5554C17.0942 15.0725 16.7384 15.0217 15.2517 14.9836C13.7268 14.9455 13.6887 14.9455 14.6417 15.0471C16.0903 15.1996 17.6025 15.5935 19.5594 16.3432C22.6726 17.5123 24.2737 17.7664 26.3195 17.4106C28.5687 17.0294 30.0935 16.2416 32.1394 14.4626C34.8333 12.1118 36.2056 11.2731 38.315 10.7013C39.7255 10.3328 42.2542 10.2947 43.5249 10.6505C45.5199 11.1969 47.0066 12.061 48.6967 13.6748C49.8784 14.8057 49.7641 14.5134 48.4807 13.1029C46.7271 11.1969 44.5288 9.8118 42.1907 9.12562C40.7166 8.69358 37.8957 8.57921 36.4725 8.89689Z"
              fill="url(#paint2_linear_20_195)"
              variants={elementVariants}
            />
            <motion.path
              d="M39.5224 12.4549C38.76 12.5819 37.6036 12.9123 36.8666 13.23C35.7611 13.6874 34.8589 14.3482 33.2959 15.8222C31.7202 17.2963 30.8434 17.9062 29.4711 18.478C27.9208 19.1261 26.7518 19.3675 25.2396 19.3675C23.6131 19.3675 22.7363 19.1642 21.4275 18.478C20.9065 18.1985 20.4491 17.9951 20.4237 18.0206C20.2966 18.1603 22.533 19.7106 23.6385 20.2443C26.3833 21.5912 29.1026 21.731 31.4407 20.6382C32.3937 20.1935 33.2197 19.5962 34.5412 18.4018C37.3749 15.8349 39.408 14.92 42.3561 14.92C44.4146 14.92 46.3969 15.4918 48.1251 16.6101C49.0781 17.22 50.7427 18.8084 51.3527 19.6852C51.6068 20.0664 51.8482 20.3841 51.8609 20.3841C51.9626 20.3841 51.4797 19.4056 50.9714 18.5797C49.2052 15.6825 46.4096 13.4841 43.5632 12.7598C42.5848 12.5057 40.2975 12.3405 39.5224 12.4549Z"
              fill="url(#paint3_linear_20_195)"
              variants={elementVariants}
            />
            <motion.path
              d="M9.50809 16.3051C7.46225 16.8642 5.69597 17.8172 4.08217 19.2277C3.56118 19.6852 2.6971 20.4476 2.17611 20.9051C1.65512 21.3625 0.892695 21.9216 0.486068 22.1504C0.0794421 22.3791 -0.111164 22.5189 0.0667351 22.468C0.638553 22.3155 1.50263 21.82 3.17997 20.7017C6.21696 18.6813 7.60203 18.173 10.0418 18.1857C11.249 18.1857 11.8208 18.262 12.8246 18.5288C15.1119 19.1261 16.7511 20.1045 19.1273 22.2901C22.2152 25.1365 24.5787 26.2675 27.73 26.4454C30.5129 26.5978 32.3681 26.0006 35.799 23.8531C38.6708 22.0487 40.2973 21.5023 42.6862 21.5023C44.4271 21.5023 45.4691 21.7437 47.0448 22.4934C48.5442 23.205 50.2088 24.7426 51.1619 26.2802C51.8862 27.4365 51.8862 27.1697 51.1492 25.6956C49.9547 23.3067 47.9597 21.3244 45.647 20.257C44.4271 19.6852 43.4741 19.4819 41.7459 19.4056C39.3189 19.304 38.0863 19.6344 35.583 21.0321C33.4228 22.2393 32.5714 22.6459 31.3643 23.0017C29.814 23.4719 27.4378 23.51 25.9383 23.078C24.0704 22.5443 22.7362 21.7564 20.7411 20.0156C18.2887 17.8808 17.1705 17.1946 15.0611 16.5084C13.5744 16.0255 10.9059 15.9366 9.50809 16.3051Z"
              fill="url(#paint4_linear_20_195)"
              variants={elementVariants}
            />
            <defs>
              <linearGradient
                id="paint0_linear_20_195"
                x1="4.83008"
                y1="5.92889"
                x2="57.8559"
                y2="5.92889"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0.341346" stopColor="#DC1A68" />
                <stop offset="0.697115" stopColor="#52002F" />
              </linearGradient>
              <linearGradient
                id="paint1_linear_20_195"
                x1="3.5708"
                y1="10.5954"
                x2="47.9983"
                y2="10.5954"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0.259615" stopColor="#DC1A68" />
                <stop offset="0.880576" stopColor="#52002F" />
              </linearGradient>
              <linearGradient
                id="paint2_linear_20_195"
                x1="14.0015"
                y1="13.1375"
                x2="49.5173"
                y2="13.1375"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0.259615" stopColor="#DC1A68" />
                <stop offset="0.793639" stopColor="#52002F" />
              </linearGradient>
              <linearGradient
                id="paint3_linear_20_195"
                x1="20.4185"
                y1="16.8925"
                x2="51.8746"
                y2="16.8925"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0.190763" stopColor="#DC1A68" />
                <stop offset="0.692308" stopColor="#52002F" />
              </linearGradient>
              <linearGradient
                id="paint4_linear_20_195"
                x1="0"
                y1="21.5391"
                x2="51.7035"
                y2="21.5391"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0.157178" stopColor="#DC1A68" />
                <stop offset="0.789484" stopColor="#52002F" />
              </linearGradient>
            </defs>
          </motion.svg>

          <motion.div
            className="absolute w-3/4 h-2 bg-pink-900/10 rounded-full blur-md"
            style={{
              bottom: '-10px',
              left: '50%',
              transform: 'translateX(-50%)',
              transformOrigin: 'center',
            }}
            variants={shadowVariants}
            animate={shadowControls}
            initial="assemble"
          />
        </motion.div>

        <motion.h1
          className={`text-5xl font-bold whitespace-nowrap ${kalnia.className} overflow-hidden`}
          style={{
            backgroundImage:
              'linear-gradient(to right, var(--auth-accent) 0%, var(--auth-accent) 40%, var(--salon-plum) 77%, var(--auth-button) 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
          variants={textVariants}
          animate={textControls}
          initial="hidden"
        >
          TIEN SALON
        </motion.h1>
      </div>
    </main>
  );
}
