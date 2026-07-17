import React, { useId } from "react";

type InfraSpendLogoProps = React.SVGProps<SVGSVGElement> & {
  title?: string;
  showWordmark?: boolean;
};

export default function InfraSpendLogo({
  title = "InfraSpend",
  showWordmark = true,
  ...props
}: InfraSpendLogoProps) {
  const generatedId = useId().replace(/:/g, "");
  const gradientId = `infraspend-mark-${generatedId}`;
  const titleId = title ? `infraspend-logo-title-${generatedId}` : undefined;
  const viewBox = showWordmark ? "0 0 690 180" : "0 0 180 180";

  return (
    <svg
      viewBox={viewBox}
      role="img"
      aria-labelledby={titleId}
      xmlns="http://www.w3.org/2000/svg"
      {...props}
    >
      {title ? <title id={titleId}>{title}</title> : null}
      <defs>
        <linearGradient id={gradientId} x1="18" y1="20" x2="164" y2="158" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0B63B6" />
          <stop offset="1" stopColor="#14B8A6" />
        </linearGradient>
      </defs>

      <path
        d="M90 8L160.15 49V131L90 172L19.85 131V49L90 8Z"
        fill={`url(#${gradientId})`}
      />
      <path
        d="M60 62L90 36L120 62L90 90M90 90L60 118L90 144L120 118L90 90M60 62L90 90L120 62M60 118L90 90L120 118"
        fill="none"
        stroke="#FFFFFF"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="7"
      />
      <circle cx="90" cy="36" r="10" fill="#FFFFFF" />
      <circle cx="60" cy="62" r="10" fill="#FFFFFF" />
      <circle cx="120" cy="62" r="10" fill="#FFFFFF" />
      <circle cx="90" cy="90" r="10" fill="#FFFFFF" />
      <circle cx="60" cy="118" r="10" fill="#FFFFFF" />
      <circle cx="120" cy="118" r="10" fill="#FFFFFF" />
      <circle cx="90" cy="144" r="10" fill="#FFFFFF" />

      {showWordmark ? (
        <>
          <text
            x="198"
            y="112"
            fill="currentColor"
            fontFamily="Poppins, DM Sans, Arial, sans-serif"
            fontSize="72"
            fontWeight="800"
            letterSpacing="0"
          >
            InfraSpend
          </text>
          <path
            d="M455 133C488 119 520 145 555 128C576 118 592 116 617 123"
            fill="none"
            stroke="#14B8A6"
            strokeLinecap="round"
            strokeWidth="8"
          />
        </>
      ) : null}
    </svg>
  );
}
