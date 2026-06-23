import { Pressable, StyleSheet, Text, View } from "react-native";
import { AI_CHOICE, type Category } from "./catalog";
import { useTrackBuilder } from "./TrackBuilderContext";

export function CategorySection({ category }: { category: Category }) {
  const { selections, select } = useTrackBuilder();
  const selected = selections[category.id];
  const aiSelected = selected === AI_CHOICE;
  return (
    <View style={styles.section}>
      <Text style={styles.heading}>{category.label}</Text>

      {/* AI Choice — the default, visually distinct from the concrete options. */}
      <Pressable
        testID={`option-${category.id}-${AI_CHOICE}`}
        accessibilityRole="radio"
        accessibilityState={{ selected: aiSelected }}
        onPress={() => select(category.id, AI_CHOICE)}
        style={[styles.aiOption, aiSelected && styles.aiOptionSelected]}
      >
        <Text style={styles.aiName}>✨ AI Choice</Text>
        <Text style={styles.optionBlurb}>Let the AI pick this for you — revealed in your track.</Text>
      </Pressable>

      {category.options.map((opt) => {
        const isSelected = selected === opt.id;
        return (
          <Pressable
            key={opt.id}
            testID={`option-${category.id}-${opt.id}`}
            accessibilityRole="radio"
            accessibilityState={{ selected: isSelected }}
            onPress={() => select(category.id, opt.id)}
            style={[styles.option, isSelected && styles.optionSelected]}
          >
            <Text style={styles.optionName}>{opt.name}</Text>
            <Text style={styles.optionBlurb}>{opt.blurb}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  section: { marginTop: 24, gap: 8 },
  heading: { fontSize: 18, fontWeight: "600" },
  option: { borderWidth: 1, borderColor: "#ddd", borderRadius: 10, padding: 12 },
  optionSelected: { borderColor: "#4338ca", backgroundColor: "#eef2ff" },
  optionName: { fontSize: 15, fontWeight: "500" },
  optionBlurb: { fontSize: 13, color: "#666", marginTop: 2 },
  // Distinct from concrete options: accent dashed border + tinted fill, stronger when selected.
  aiOption: {
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: "#7c3aed",
    borderRadius: 10,
    padding: 12,
    backgroundColor: "#faf5ff",
  },
  aiOptionSelected: { borderStyle: "solid", borderColor: "#7c3aed", backgroundColor: "#f3e8ff" },
  aiName: { fontSize: 15, fontWeight: "700", color: "#6d28d9" },
});
