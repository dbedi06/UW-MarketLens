// Shows the dynamic OG card the snapshot link previews as when shared.
// The image is generated server-side from the snapshot's real data.

import { motion } from "framer-motion";
import { fadeUp } from "../lib/motion";
import { ogImageUrl } from "../api";
import SectionHeading from "../ui/SectionHeading";

export default function SocialPreview({
  snapshotId,
  score,
}: {
  snapshotId: string;
  score?: number;
}) {
  return (
    <motion.div variants={fadeUp} className="card p-6">
      <SectionHeading
        eyebrow="Share"
        title="Social preview"
        sub="How this snapshot link appears when shared. Generated from the snapshot's exact data, so the preview always matches the report."
      />
      <div className="overflow-hidden rounded-lg border border-line">
        <img
          src={ogImageUrl(snapshotId, score)}
          alt="Social share card for this reliability snapshot"
          width={1200}
          height={630}
          loading="lazy"
          className="block aspect-[1200/630] w-full"
        />
      </div>
    </motion.div>
  );
}
