# ✅ CRASHLENS WORKFLOW DEPLOYMENT CHECKLIST

## 🚀 **IMMEDIATE DEPLOYMENT STEPS**

### **Phase 1: Basic Deployment (5 minutes)**

- [ ] **Copy improved workflow to your project:**
  ```bash
  mkdir -p .github/workflows
  cp IMPROVED_WORKFLOW.yml .github/workflows/crashlens.yml
  ```

- [ ] **Verify Crashlens version in workflow:**
  ```yaml
  # Should show: pip install crashlens==2.9.1
  grep "crashlens==" .github/workflows/crashlens.yml
  ```

- [ ] **Commit and push:**
  ```bash
  git add .github/workflows/crashlens.yml
  git commit -m "Add production-ready Crashlens workflow v2.9.1"
  git push origin main
  ```

- [ ] **Monitor first workflow run:**
  - Go to GitHub Actions tab
  - Watch the workflow execute
  - Verify all steps complete successfully

### **Phase 2: Verification (10 minutes)**

- [ ] **Check workflow artifacts:**
  - Download artifacts from completed run
  - Verify reports are generated
  - Confirm JSON/Markdown formats are correct

- [ ] **Test PR integration:**
  - Create a test PR
  - Verify workflow runs on PR
  - Check PR comment is posted with results

- [ ] **Review analysis reports:**
  - Open `final-crashlens-report.md`
  - Check `retry-analysis-report.md` 
  - Verify `performance-analysis-results.json`

### **Phase 3: Customization (15 minutes)**

- [ ] **Adjust policy templates (if needed):**
  ```yaml
  # In the workflow, modify this line:
  CRASHLENS_TEMPLATES: "retry-loop-prevention,model-overkill-detection,budget-protection"
  ```

- [ ] **Set severity threshold:**
  ```yaml
  # Options: low, medium, high, critical
  CRASHLENS_SEVERITY: "high"
  ```

- [ ] **Configure failure behavior:**
  ```yaml
  # Set to "true" to fail CI on violations
  CRASHLENS_FAIL_ON_VIOLATIONS: "false"
  ```

### **Phase 4: Advanced Setup (Optional)**

- [ ] **Add API secrets (if using real data):**
  - Go to Settings > Secrets and variables > Actions
  - Add `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `HELICONE_API_KEY`

- [ ] **Set up notifications:**
  ```yaml
  # Add Slack webhook for alerts
  SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
  ```

- [ ] **Configure schedule (optional):**
  ```yaml
  # Modify cron schedule if needed (currently daily at 6 AM UTC)
  - cron: '0 6 * * *'
  ```

---

## 🧪 **TESTING CHECKLIST**

### **Local Testing (Before deployment):**

- [ ] **Verify Crashlens installation:**
  ```bash
  poetry run crashlens --version
  # Should output: crashlens, version 2.9.1
  ```

- [ ] **Test policy check locally:**
  ```bash
  poetry run crashlens simulate --output test.jsonl --count 10
  poetry run crashlens policy-check test.jsonl --policy-template all
  ```

- [ ] **Validate configuration:**
  ```bash
  poetry run crashlens init --non-interactive
  cat .crashlens/config.yaml
  ```

### **GitHub Actions Testing:**

- [ ] **First run validation:**
  - Workflow completes without errors
  - All steps show green checkmarks
  - Artifacts are uploaded successfully

- [ ] **Report quality check:**
  - Markdown reports are well-formatted
  - JSON files contain valid data
  - Performance analysis shows realistic metrics

- [ ] **PR integration test:**
  - Create test PR with dummy changes
  - Verify workflow triggers automatically
  - Check PR comment appears with analysis

---

## 📊 **SUCCESS CRITERIA**

Your deployment is successful when:

### **✅ Technical Success:**
- [ ] Workflow runs without failures
- [ ] All 5 analysis components complete
- [ ] Artifacts are generated and downloadable
- [ ] PR comments include analysis summaries
- [ ] No missing dependencies or file errors

### **✅ Functional Success:**
- [ ] Policy violations are detected in test data
- [ ] Reports contain actionable insights
- [ ] Performance metrics are reasonable
- [ ] Security scans complete successfully
- [ ] Test data generation works as expected

### **✅ Operational Success:**
- [ ] Team can interpret reports easily
- [ ] Workflow integrates smoothly with existing CI/CD
- [ ] No impact on deployment pipeline performance
- [ ] Documentation is clear and accessible

---

## 🚨 **ROLLBACK PLAN (If Needed)**

If any issues arise:

1. **Disable workflow temporarily:**
   ```bash
   # Rename or delete the workflow file
   mv .github/workflows/crashlens.yml .github/workflows/crashlens.yml.disabled
   git commit -m "Temporarily disable Crashlens workflow"
   git push
   ```

2. **Check logs for errors:**
   - Review GitHub Actions logs
   - Look for specific error messages
   - Check dependency installation steps

3. **Common fixes:**
   ```yaml
   # If Poetry issues, try pip-only approach:
   - run: pip install crashlens==2.9.1
   
   # If permission issues, add:
   permissions:
     contents: read
     issues: write
     pull-requests: write
   ```

4. **Re-enable after fixes:**
   ```bash
   mv .github/workflows/crashlens.yml.disabled .github/workflows/crashlens.yml
   git commit -m "Re-enable fixed Crashlens workflow"
   git push
   ```

---

## 📞 **SUPPORT RESOURCES**

### **If You Need Help:**

1. **Check workflow logs** for specific error messages
2. **Review the USER_MANUAL.md** for troubleshooting tips
3. **Test locally first** before debugging CI/CD issues
4. **Use the GitHub Issues** in the Crashlens repository for questions

### **Common Commands for Debugging:**

```bash
# Test Crashlens locally
poetry run crashlens --version
poetry run crashlens list-policy-templates
poetry run crashlens simulate --help

# Check workflow file syntax
yamllint .github/workflows/crashlens.yml

# Validate Poetry configuration
poetry check
poetry show crashlens
```

---

## 🎯 **POST-DEPLOYMENT ACTIONS**

### **Week 1: Monitor & Adjust**
- [ ] Review all workflow runs for patterns
- [ ] Adjust policy templates based on findings
- [ ] Fine-tune sensitivity thresholds
- [ ] Share initial insights with team

### **Week 2: Optimize & Scale**
- [ ] Configure real data sources if needed
- [ ] Set up automated alerts for critical violations
- [ ] Document team processes for reviewing reports
- [ ] Plan regular policy review cadence

### **Month 1: Measure Impact**
- [ ] Calculate token savings achieved
- [ ] Document efficiency improvements
- [ ] Train additional team members
- [ ] Consider expanding to other projects

---

**🚀 Ready to Deploy! Your Crashlens workflow is production-ready and will provide immediate value for token waste detection!** 

*Estimated deployment time: 15-30 minutes for complete setup*
