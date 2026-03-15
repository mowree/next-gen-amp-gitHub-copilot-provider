#!/bin/bash
# =============================================================================
# validate-recipes.sh — Validate .dev-machine recipes against bundle schema
# =============================================================================
#
# PURPOSE:
#   Invokes the amplifier bundle's validate-recipes.yaml recipe to check
#   that all recipes in .dev-machine/ conform to the expected schema.
#
# WHEN TO USE:
#   - After modifying any .dev-machine/*.yaml recipe
#   - Before committing recipe changes
#   - When debugging recipe execution failures
#
# CREATED: 2026-03-08 (migrated from temp_validate.sh)
# MACHINE: WSL environment
#
# USAGE:
#   ./.tools/validate-recipes.sh
#
# =============================================================================

cd /mnt/d/next-get-provider-github-copilot
amplifier tool invoke recipes operation=execute \
  recipe_path="/home/mowrim/.amplifier/cache/amplifier-bundle-recipes-2b1e350432fea9ba/recipes/validate-recipes.yaml" \
  context='{"repo_path": ".", "recipes_dir": ".dev-machine"}'
