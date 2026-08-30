/**
 * Always visible, never dismissible (§6). This is a standing requirement of the
 * project, not decoration — do not add a close button.
 */
export default function DisclaimerBar() {
  return (
    <div className="shrink-0 border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900">
      <strong>Informational only.</strong> This assistant explains verified health reference
      material. It is not medical advice and not a substitute for professional diagnosis. In an
      emergency in India, call <strong>112</strong> or an ambulance on <strong>108</strong>.
    </div>
  )
}
