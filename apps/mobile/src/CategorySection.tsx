import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Category } from "./catalog";
import { useTrackBuilder } from "./TrackBuilderContext";

export function CategorySection({ category }: { category: Category }) {
  const { selections, select } = useTrackBuilder();
  const selected = selections[category.id];
  return (
    <View style={styles.section}>
      <Text style={styles.heading}>{category.label}</Text>
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
});
